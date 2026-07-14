"""Validate the live-canary topology before any container is started.

Unlike the fully-offline HA pod, this canary uses two rootless Podman networks:
runner/Selenium are attached only to an internal network, while the minimal
allowlist proxy is the sole dual-homed container.  The validator is intentionally
strict and writes only topology metadata, never fixture values or container logs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

PROXY_SERVER_ARGUMENT = "--proxy-server=http://ukbcd-live-proxy:3128"
# Chromium has an implicit loopback bypass.  The special <-loopback> token
# subtracts it, leaving no hosts outside the proxy policy.
PROXY_NO_BYPASS_ARGUMENT = "--proxy-bypass-list=<-loopback>"
APPROVAL_ENVIRONMENT_VARIABLE = "UKBCD_LIVE_CANARY_APPROVED"
APPROVAL_VALUE = "one-public-fixture-lookup"
HOST_NAMESPACE_FIELDS = (
    "PidMode",
    "IpcMode",
    "UsernsMode",
    "UTSMode",
    "CgroupnsMode",
    "CgroupMode",
)
RUNNER_PROCESS = (
    "python",
    (
        "/opt/ukbcd/live_canary_runner.py",
        "--confirm-one-public-fixture-lookup",
    ),
)
PROXY_PROCESS = (
    "python3",
    (
        "/opt/ukbcd/live_allowlist_proxy.py",
        "--max-requests",
        "256",
        "--minimum-interval-ms",
        "25",
    ),
)
_SHA256_PATTERN = re.compile(r"^(?:sha256:)?([0-9a-fA-F]{64})$")
_CAPABILITY_PATTERN = re.compile(r"^(?:CAP_)?[A-Z][A-Z0-9_]*$")
SENSITIVE_ENVIRONMENT_NAME_MARKERS = frozenset(
    {
        "token",
        "password",
        "passwd",
        "secret",
        "credential",
        "postcode",
        "house_number",
        "housenumber",
        "house_name",
        "housename",
        "paon",
        "uprn",
        "usrn",
        "address",
    }
)


def _podman_json(*arguments: str):
    result = subprocess.run(
        ["podman", *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _inspect_container(name: str) -> dict:
    return _podman_json("inspect", name)[0]


def _inspect_image(image_id: str) -> dict:
    return _podman_json("image", "inspect", image_id)[0]


def _inspect_network(name: str) -> dict:
    return _podman_json("network", "inspect", name)[0]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _is_internal(network: dict) -> bool:
    return bool(network.get("internal", network.get("Internal", False)))


def _is_rootless(info: dict) -> bool:
    reported_values: list[object] = []
    if "rootless" in info.get("host", {}).get("security", {}):
        reported_values.append(info["host"]["security"]["rootless"])
    if "Rootless" in info.get("Host", {}).get("Security", {}):
        reported_values.append(info["Host"]["Security"]["Rootless"])
    return bool(reported_values) and all(value is True for value in reported_values)


def _attached_networks(container: dict) -> set[str]:
    return set(container.get("NetworkSettings", {}).get("Networks", {}))


def _environment(container: dict) -> set[str]:
    return set(container.get("Config", {}).get("Env") or [])


def _environment_mapping(subject: dict) -> dict[str, str]:
    environment: dict[str, str] = {}
    for raw_value in subject.get("Config", {}).get("Env") or []:
        variable_name, separator, value = str(raw_value).partition("=")
        if variable_name:
            environment[variable_name] = value if separator else ""
    return environment


def _is_sensitive_environment_name(variable_name: str) -> bool:
    normalized_name = variable_name.casefold()
    return any(
        marker in normalized_name for marker in SENSITIVE_ENVIRONMENT_NAME_MARKERS
    )


def _require_no_sensitive_environment_overrides(
    name: str, container: dict, image: dict
) -> None:
    """Reject sensitive runtime env not identically baked into the reviewed image."""
    container_environment = _environment_mapping(container)
    reviewed_environment = _environment_mapping(image)
    sensitive_overrides = sorted(
        variable_name
        for variable_name, value in container_environment.items()
        if _is_sensitive_environment_name(variable_name)
        and reviewed_environment.get(variable_name) != value
    )
    _require(
        not sensitive_overrides,
        f"{name} receives a sensitive environment override: {sensitive_overrides}",
    )


def _network_members(network: dict) -> set[str]:
    """Extract actual container names from a Podman network-inspect result."""
    raw_members = network.get("containers", network.get("Containers"))
    if isinstance(raw_members, dict):
        rows = raw_members.values()
    elif isinstance(raw_members, list):
        rows = raw_members
    else:
        return set()

    members: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name", row.get("Name"))
        if isinstance(name, str) and name:
            members.add(name)
    return members


def _require_exact_members(boundary: str, actual: set[str], expected: set[str]) -> None:
    missing = expected - actual
    extra = actual - expected
    _require(
        not missing and not extra,
        f"{boundary} membership mismatch; missing={sorted(missing)} extra={sorted(extra)}",
    )


def _normalise_capability(value: object) -> str:
    capability = str(value).strip().upper()
    return capability.removeprefix("CAP_")


def _parse_capabilities(value: object) -> frozenset[str]:
    """Parse one concrete capability universe reported by Podman."""
    if isinstance(value, str):
        raw_capabilities = [] if not value.strip() else value.split(",")
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        raw_capabilities = value
    else:
        raise RuntimeError("Podman reports malformed rootless capabilities")

    capabilities: set[str] = set()
    for raw_capability in raw_capabilities:
        normalized_input = raw_capability.strip().upper()
        _require(
            bool(_CAPABILITY_PATTERN.fullmatch(normalized_input)),
            "Podman reports malformed rootless capabilities",
        )
        capability = _normalise_capability(normalized_input)
        _require(
            capability != "ALL",
            "Podman rootless capability universe must contain concrete names",
        )
        capabilities.add(capability)
    return frozenset(capabilities)


def _rootless_capabilities(info: dict) -> frozenset[str]:
    """Return the exact capability universe advertised by the rootless engine."""
    reported: list[frozenset[str]] = []
    lower_security = info.get("host", {}).get("security", {})
    if "capabilities" in lower_security:
        reported.append(_parse_capabilities(lower_security["capabilities"]))
    upper_security = info.get("Host", {}).get("Security", {})
    if "Capabilities" in upper_security:
        reported.append(_parse_capabilities(upper_security["Capabilities"]))

    _require(bool(reported), "Podman does not report rootless capabilities")
    _require(
        all(value == reported[0] for value in reported[1:]),
        "Podman reports conflicting rootless capability universes",
    )
    return reported[0]


def _create_command_requests_cap_drop_all(container: dict) -> bool:
    command = container.get("Config", {}).get("CreateCommand") or []
    if not isinstance(command, list):
        return False
    tokens = [str(token).casefold() for token in command]
    if "--cap-drop=all" in tokens:
        return True
    return any(
        token == "--cap-drop" and index + 1 < len(tokens) and tokens[index + 1] == "all"
        for index, token in enumerate(tokens)
    )


def _cap_drop_covers_available_set(
    container: dict, available_capabilities: frozenset[str]
) -> bool:
    host = container.get("HostConfig", {})
    raw_drops = host.get("CapDrop")
    _require(
        isinstance(raw_drops, list)
        and all(isinstance(value, str) for value in raw_drops),
        "Podman reports malformed dropped capabilities",
    )
    drops: set[str] = set()
    for value in raw_drops:
        normalized_input = value.strip().upper()
        _require(
            bool(_CAPABILITY_PATTERN.fullmatch(normalized_input)),
            "Podman reports malformed dropped capabilities",
        )
        drops.add(_normalise_capability(normalized_input))
    return "ALL" in drops or available_capabilities <= drops


def _require_cap_drop_all(
    name: str, container: dict, available_capabilities: frozenset[str]
) -> None:
    cap_add = container.get("HostConfig", {}).get("CapAdd")
    _require(
        isinstance(cap_add, list),
        f"{name} reports malformed added capabilities",
    )
    _require(
        _create_command_requests_cap_drop_all(container),
        f"{name} was not created with --cap-drop all",
    )
    _require(
        not cap_add,
        f"{name} adds Linux capabilities",
    )
    _require(
        _cap_drop_covers_available_set(container, available_capabilities),
        f"{name} does not report the complete rootless capability drop set",
    )


def _host_namespace_modes(container: dict) -> dict[str, str]:
    host = container.get("HostConfig", {})
    return {
        field: str(host[field])
        for field in HOST_NAMESPACE_FIELDS
        if field in host
        and str(host[field]).strip().casefold().split(":", 1)[0] == "host"
    }


def _require_no_host_namespaces(name: str, container: dict) -> None:
    host_modes = _host_namespace_modes(container)
    _require(
        not host_modes,
        f"{name} joins host namespaces: {sorted(host_modes)}",
    )


def _normalise_image_id(value: object) -> str | None:
    text = str(value).strip()
    match = _SHA256_PATTERN.fullmatch(text)
    if not match:
        return None
    return f"sha256:{match.group(1).lower()}"


def _inspected_image_ids(container: dict) -> set[str]:
    identifiers: set[str] = set()
    for field in ("Image", "ImageID", "ImageDigest", "Digest"):
        if field not in container:
            continue
        normalized = _normalise_image_id(container[field])
        if normalized is not None:
            identifiers.add(normalized)
    return identifiers


def _require_expected_image(name: str, container: dict, expected: str) -> str:
    normalized_expected = _normalise_image_id(expected)
    _require(
        normalized_expected is not None,
        f"{name} expected image must be a full immutable SHA-256 ID or digest",
    )
    actual_ids = _inspected_image_ids(container)
    _require(bool(actual_ids), f"{name} inspect data has no immutable image ID")
    _require(
        normalized_expected in actual_ids,
        f"{name} immutable image ID does not match the reviewed value",
    )
    return normalized_expected


def _require_exact_process(
    name: str,
    container: dict,
    expected: tuple[str, tuple[str, ...]],
) -> None:
    actual = (str(container.get("Path", "")), tuple(container.get("Args") or []))
    _require(actual == expected, f"{name} entrypoint or arguments differ from policy")


def _process_sha256(container: dict) -> str:
    payload = {
        "path": str(container.get("Path", "")),
        "args": [str(value) for value in container.get("Args") or []],
    }
    serialized = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(serialized).hexdigest()}"


def _require_expected_process(name: str, container: dict, expected: str) -> str:
    normalized_expected = _normalise_image_id(expected)
    _require(
        normalized_expected is not None,
        f"{name} expected process must be a full SHA-256 digest",
    )
    actual = _process_sha256(container)
    _require(
        actual == normalized_expected,
        f"{name} entrypoint or arguments differ from the reviewed payload",
    )
    return actual


def _reviewed_image_process_sha256(image: dict) -> str:
    config = image.get("Config", {})
    entrypoint = config.get("Entrypoint") or []
    command = config.get("Cmd") or []
    _require(
        isinstance(entrypoint, list) and isinstance(command, list),
        "reviewed Selenium image process metadata is malformed",
    )
    process = [str(value) for value in [*entrypoint, *command]]
    _require(
        bool(process) and bool(process[0].strip()),
        "reviewed Selenium image has no default process",
    )
    return _process_sha256({"Path": process[0], "Args": process[1:]})


def _validate_container(
    name: str,
    container: dict,
    *,
    expected_networks: set[str],
    available_capabilities: frozenset[str],
) -> dict:
    host = container["HostConfig"]
    _require(container["State"]["Status"] == "created", f"{name} already started")
    _require(not container.get("Pod"), f"{name} unexpectedly belongs to a pod")
    _require(not host["Privileged"], f"{name} is privileged")
    _require(host["ReadonlyRootfs"], f"{name} root filesystem is writable")
    _require(not host.get("PortBindings"), f"{name} publishes a host port")
    _require(not host.get("PublishAllPorts"), f"{name} publishes all ports")
    _require(not host.get("Devices"), f"{name} receives a host device")
    _require_cap_drop_all(name, container, available_capabilities)
    _require_no_host_namespaces(name, container)
    _require(
        "no-new-privileges" in host.get("SecurityOpt", []),
        f"{name} permits privilege escalation",
    )
    _require(
        host.get("RestartPolicy", {}).get("Name") in ("", "no"),
        f"{name} has a restart policy",
    )
    _require(host.get("PidsLimit", 0) > 0, f"{name} has no PID limit")
    _require(host.get("NanoCpus", 0) > 0, f"{name} has no CPU limit")
    _require(host.get("Memory", 0) > 0, f"{name} has no memory limit")
    _require(not container.get("Mounts"), f"{name} has a mount")
    _require(
        host.get("NetworkMode") not in {"host", "none"}
        and not str(host.get("NetworkMode", "")).startswith("container:"),
        f"{name} uses an unexpected network namespace",
    )

    networks = _attached_networks(container)
    _require(
        networks == expected_networks,
        f"{name} networks differ from policy: {sorted(networks)}",
    )

    serialized = json.dumps(container).casefold()
    _require("podman.sock" not in serialized, f"{name} receives the Podman socket")
    _require("docker.sock" not in serialized, f"{name} receives the Docker socket")
    _require("/mnt/" not in serialized, f"{name} references a Windows-drive mount")

    return {
        "state": "created",
        "read_only_rootfs": True,
        "privileged": False,
        "networks": sorted(networks),
        "published_ports": 0,
        "mounts": 0,
        "devices": 0,
        "capabilities_added": 0,
        "capabilities_dropped": "all",
        "rootless_capabilities_dropped": sorted(available_capabilities),
        "cap_drop_all": True,
        "host_namespaces": [],
        "no_new_privileges": True,
        "pid_limit": host["PidsLimit"],
        "cpu_limit": host["NanoCpus"] / 1_000_000_000,
        "memory_limit_bytes": host["Memory"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--internal-network", required=True)
    parser.add_argument("--egress-network", required=True)
    parser.add_argument("--runner", required=True)
    parser.add_argument("--selenium", required=True)
    parser.add_argument("--proxy", required=True)
    parser.add_argument("--expected-proxy-image", required=True)
    parser.add_argument("--expected-selenium-image", required=True)
    parser.add_argument("--expected-runner-image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    info = _podman_json("info", "--format", "json")
    _require(_is_rootless(info), "Podman is not running rootless")
    available_capabilities = _rootless_capabilities(info)

    internal = _inspect_network(args.internal_network)
    egress = _inspect_network(args.egress_network)
    _require(_is_internal(internal), "runner/Selenium network is not internal")
    _require(not _is_internal(egress), "proxy egress network is marked internal")
    _require(
        internal.get("driver", internal.get("Driver")) == "bridge",
        "runner/Selenium network is not a rootless bridge",
    )
    _require(
        egress.get("driver", egress.get("Driver")) == "bridge",
        "proxy egress network is not a rootless bridge",
    )
    internal_members = _network_members(internal)
    egress_members = _network_members(egress)
    _require_exact_members(
        args.internal_network,
        internal_members,
        {args.runner, args.selenium, args.proxy},
    )
    _require_exact_members(args.egress_network, egress_members, {args.proxy})

    runner = _inspect_container(args.runner)
    selenium = _inspect_container(args.selenium)
    proxy = _inspect_container(args.proxy)
    image_ids = {
        args.runner: _require_expected_image(
            args.runner, runner, args.expected_runner_image
        ),
        args.selenium: _require_expected_image(
            args.selenium, selenium, args.expected_selenium_image
        ),
        args.proxy: _require_expected_image(
            args.proxy, proxy, args.expected_proxy_image
        ),
    }
    containers = {
        args.runner: runner,
        args.selenium: selenium,
        args.proxy: proxy,
    }
    images: dict[str, dict] = {}
    for name, container in containers.items():
        images[name] = _inspect_image(image_ids[name])
        _require_no_sensitive_environment_overrides(name, container, images[name])
    checks = {
        args.runner: _validate_container(
            args.runner,
            runner,
            expected_networks={args.internal_network},
            available_capabilities=available_capabilities,
        ),
        args.selenium: _validate_container(
            args.selenium,
            selenium,
            expected_networks={args.internal_network},
            available_capabilities=available_capabilities,
        ),
        args.proxy: _validate_container(
            args.proxy,
            proxy,
            expected_networks={args.internal_network, args.egress_network},
            available_capabilities=available_capabilities,
        ),
    }
    selenium_environment = _environment(selenium)
    expected_proxy_environment = {
        f"SE_BROWSER_ARGS_UKBCD_PROXY={PROXY_SERVER_ARGUMENT}",
        f"SE_BROWSER_ARGS_UKBCD_NO_BYPASS={PROXY_NO_BYPASS_ARGUMENT}",
        "SE_BROWSER_ARGS_UKBCD_BACKGROUND=--disable-background-networking",
        "SE_BROWSER_ARGS_UKBCD_SYNC=--disable-sync",
        "SE_BROWSER_ARGS_UKBCD_DEFAULT_APPS=--disable-default-apps",
    }
    _require(
        expected_proxy_environment <= selenium_environment,
        "Selenium does not contain the reviewed Chrome proxy arguments",
    )
    bypass_values = {
        value
        for value in selenium_environment
        if "proxy-bypass-list" in value.casefold()
    }
    _require(
        bypass_values
        == {f"SE_BROWSER_ARGS_UKBCD_NO_BYPASS={PROXY_NO_BYPASS_ARGUMENT}"},
        "Selenium contains an additional proxy bypass rule",
    )

    runner_environment = _environment(runner)
    _require(
        f"{APPROVAL_ENVIRONMENT_VARIABLE}={APPROVAL_VALUE}" in runner_environment,
        "runner lacks the exact one-shot approval value",
    )

    _require_exact_process(args.runner, runner, RUNNER_PROCESS)
    _require_exact_process(args.proxy, proxy, PROXY_PROCESS)
    selenium_process_digest = _require_expected_process(
        args.selenium,
        selenium,
        _reviewed_image_process_sha256(images[args.selenium]),
    )
    checks[args.selenium]["process_sha256"] = selenium_process_digest

    total_cpu = sum(check["cpu_limit"] for check in checks.values())
    total_memory = sum(check["memory_limit_bytes"] for check in checks.values())
    _require(total_cpu <= 6, f"aggregate CPU limit exceeds 6: {total_cpu}")
    _require(total_memory <= 7 * 1024**3, "aggregate memory exceeds 7 GiB")

    report = {
        "status": "passed",
        "rootless": True,
        "rootless_capability_universe": sorted(available_capabilities),
        "internal_network": {
            "name": args.internal_network,
            "internal": True,
            "members": sorted(internal_members),
        },
        "egress_network": {
            "name": args.egress_network,
            "internal": False,
            "members": sorted(egress_members),
        },
        "allowlisted_origins": [
            "selfservice.southkesteven.gov.uk",
            "www.southkesteven.gov.uk",
        ],
        "application_containers": checks,
        "immutable_image_ids": image_ids,
        "aggregate_cpu_limit": total_cpu,
        "aggregate_memory_limit_bytes": total_memory,
        "host_ports": 0,
        "host_mounts": 0,
        "container_sockets": 0,
        "chrome_proxy_bypass_hosts": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
