"""Fail closed unless an unstarted disposable Podman pod is tightly contained."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

EXPECTED_DEFAULT_CAPABILITIES = frozenset(
    {
        "AUDIT_WRITE",
        "CHOWN",
        "DAC_OVERRIDE",
        "FOWNER",
        "FSETID",
        "KILL",
        "MKNOD",
        "NET_BIND_SERVICE",
        "NET_RAW",
        "SETFCAP",
        "SETGID",
        "SETPCAP",
        "SETUID",
        "SYS_CHROOT",
    }
)
HOST_NAMESPACE_FIELDS = (
    "PidMode",
    "IpcMode",
    "UsernsMode",
    "UTSMode",
    "CgroupnsMode",
    "CgroupMode",
)
_SHA256_PATTERN = re.compile(r"^(?:sha256:)?([0-9a-fA-F]{64})$")
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


def _inspect(name: str) -> dict:
    return _podman_json("inspect", name)[0]


def _inspect_image(image_id: str) -> dict:
    return _podman_json("image", "inspect", image_id)[0]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _is_rootless(info: dict) -> bool:
    reported_values: list[object] = []
    if "rootless" in info.get("host", {}).get("security", {}):
        reported_values.append(info["host"]["security"]["rootless"])
    if "Rootless" in info.get("Host", {}).get("Security", {}):
        reported_values.append(info["Host"]["Security"]["Rootless"])
    return bool(reported_values) and all(value is True for value in reported_values)


def _named_members(raw_members) -> set[str]:
    """Extract names from Podman pod/network inspect member structures."""
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
        name = row.get("Name", row.get("name"))
        if isinstance(name, str) and name:
            members.add(name)
    return members


def _pod_members(pod: dict) -> set[str]:
    return _named_members(pod.get("Containers", pod.get("containers")))


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


def _cap_drop_covers_default_set(container: dict) -> bool:
    raw_drops = container.get("HostConfig", {}).get("CapDrop") or []
    drops = {_normalise_capability(value) for value in raw_drops}
    return "ALL" in drops or EXPECTED_DEFAULT_CAPABILITIES <= drops


def _require_cap_drop_all(name: str, container: dict) -> None:
    _require(
        _create_command_requests_cap_drop_all(container),
        f"{name} was not created with --cap-drop all",
    )
    _require(
        _cap_drop_covers_default_set(container),
        f"{name} does not report the expected complete capability drop set",
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


def _normalise_sha256(value: object) -> str | None:
    match = _SHA256_PATTERN.fullmatch(str(value).strip())
    if not match:
        return None
    return f"sha256:{match.group(1).lower()}"


def _inspected_image_ids(container: dict) -> set[str]:
    identifiers: set[str] = set()
    for field in ("Image", "ImageID", "ImageDigest", "Digest"):
        if field not in container:
            continue
        normalized = _normalise_sha256(container[field])
        if normalized is not None:
            identifiers.add(normalized)
    return identifiers


def _require_expected_image(name: str, container: dict, expected: str) -> str:
    normalized_expected = _normalise_sha256(expected)
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
    normalized_expected = _normalise_sha256(expected)
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


def _parse_name_mapping(
    values: list[str], expected_names: set[str], label: str
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for value in values:
        name, separator, expected = value.partition("=")
        _require(
            bool(separator and name and expected),
            f"{label} values must use NAME=SHA256",
        )
        _require(name not in mapping, f"duplicate {label} for {name}")
        mapping[name] = expected
    _require_exact_members(label, set(mapping), expected_names)
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pod", required=True)
    parser.add_argument("--infra", required=True)
    parser.add_argument("--container", action="append", default=[], required=True)
    parser.add_argument("--expected-image", action="append", default=[], required=True)
    parser.add_argument(
        "--expected-process-sha256", action="append", default=[], required=True
    )
    parser.add_argument("--allowed-volume", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    info = _podman_json("info", "--format", "json")
    _require(_is_rootless(info), "Podman is not running rootless")

    pod = _inspect(args.pod)
    infra = _inspect(args.infra)
    infra_id = infra["Id"]
    infra_host = infra["HostConfig"]

    pod_members = _pod_members(pod)
    expected_pod_members = {args.infra, *args.container}
    _require_exact_members(args.pod, pod_members, expected_pod_members)
    container_names = set(args.container)
    expected_images = _parse_name_mapping(
        args.expected_image, container_names, "expected images"
    )
    expected_processes = _parse_name_mapping(
        args.expected_process_sha256,
        container_names,
        "expected process digests",
    )

    _require(pod["State"] == "Created", "pod was started before safety validation")
    _require(infra["State"]["Status"] == "created", "infra was already started")
    _require(
        infra["Config"]["Image"].startswith("localhost/podman-pause:"),
        "infra image is not Podman's built-in pause image",
    )
    _require(infra["Path"] == "/catatonit", "infra runs an unexpected process")
    _require_no_host_namespaces(args.infra, infra)
    _require(infra_host["NetworkMode"] == "none", "pod has a network route")
    _require(not infra_host["Privileged"], "infra is privileged")
    _require(not infra_host.get("PortBindings"), "infra publishes a host port")
    _require(not infra_host.get("Devices"), "infra has a host device")
    _require(not infra.get("Mounts"), "infra has a host or volume mount")
    _require(
        "no-new-privileges" in infra_host.get("SecurityOpt", []),
        "infra permits privilege escalation",
    )
    _require(
        infra_host.get("RestartPolicy", {}).get("Name") in ("", "no"),
        "infra has a restart policy",
    )

    allowed_volumes = set(args.allowed_volume)
    total_cpus = 0.0
    total_memory = 0
    checks: dict[str, dict] = {}
    for name in args.container:
        container = _inspect(name)
        host = container["HostConfig"]
        image_id = _require_expected_image(name, container, expected_images[name])
        _require_no_sensitive_environment_overrides(
            name, container, _inspect_image(image_id)
        )
        process_digest = _require_expected_process(
            name, container, expected_processes[name]
        )
        _require(container["State"]["Status"] == "created", f"{name} already started")
        _require(not host["Privileged"], f"{name} is privileged")
        _require(host["ReadonlyRootfs"], f"{name} root filesystem is writable")
        _require(
            host["NetworkMode"] == f"container:{infra_id}",
            f"{name} does not share the offline pod namespace",
        )
        _require(not host.get("PortBindings"), f"{name} publishes a host port")
        _require(not host.get("PublishAllPorts"), f"{name} publishes all ports")
        _require(not host.get("Devices"), f"{name} has a host device")
        _require(not host.get("CapAdd"), f"{name} adds Linux capabilities")
        _require_cap_drop_all(name, container)
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

        mounts = container.get("Mounts", [])
        _require(
            all(mount.get("Type") == "volume" for mount in mounts),
            f"{name} has a bind or non-volume mount",
        )
        mounted_names = {mount.get("Name") for mount in mounts}
        _require(
            mounted_names <= allowed_volumes,
            f"{name} has an unapproved named volume: {sorted(mounted_names)}",
        )
        serialized = json.dumps(container).casefold()
        _require("podman.sock" not in serialized, f"{name} receives the Podman socket")
        _require("docker.sock" not in serialized, f"{name} receives the Docker socket")

        total_cpus += host["NanoCpus"] / 1_000_000_000
        total_memory += host["Memory"]
        checks[name] = {
            "image_id": image_id,
            "process_sha256": process_digest,
            "read_only_rootfs": True,
            "privileged": False,
            "network_namespace": "offline-pod-loopback",
            "published_ports": 0,
            "devices": 0,
            "capabilities_added": 0,
            "capabilities_dropped": "all",
            "cap_drop_all": True,
            "host_namespaces": [],
            "no_new_privileges": True,
            "pid_limit": host["PidsLimit"],
            "cpu_limit": host["NanoCpus"] / 1_000_000_000,
            "memory_limit_bytes": host["Memory"],
            "named_volumes": sorted(mounted_names),
            "tmpfs": sorted(host.get("Tmpfs", {})),
        }

    _require(total_cpus <= 6, f"aggregate CPU limit exceeds 6: {total_cpus}")
    _require(total_memory <= 7 * 1024**3, "aggregate memory limit exceeds 7 GiB")

    report = {
        "status": "passed",
        "rootless": True,
        "pod": args.pod,
        "pod_members": sorted(pod_members),
        "pod_state_before_test": "Created",
        "infra": {
            "image": infra["Config"]["Image"],
            "process": [infra["Path"], *infra["Args"]],
            "network_mode": "none",
            "published_ports": 0,
            "devices": 0,
            "mounts": 0,
            "privileged": False,
            "no_new_privileges": True,
            "host_namespaces": [],
            "note": "Podman's static namespace-holding pause process has no application payload.",
        },
        "application_containers": checks,
        "aggregate_cpu_limit": total_cpus,
        "aggregate_memory_limit_bytes": total_memory,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
