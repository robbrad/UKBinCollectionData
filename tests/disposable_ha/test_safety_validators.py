"""Offline tests for fail-closed Podman safety validator decisions."""

from __future__ import annotations

import pytest

from tests.disposable_ha import live_canary_safety_check as live
from tests.disposable_ha import pod_safety_check as offline

VALIDATORS = (offline, live)
ROOTLESS_CAPABILITIES = frozenset(
    {
        "CHOWN",
        "DAC_OVERRIDE",
        "FOWNER",
        "FSETID",
        "KILL",
        "NET_BIND_SERVICE",
        "SETFCAP",
        "SETGID",
        "SETPCAP",
        "SETUID",
        "SYS_CHROOT",
    }
)

SENSITIVE_ENVIRONMENT_NAMES = (
    "HA_TOKEN",
    "ADMIN_PASSWORD",
    "API_SECRET",
    "CLIENT_CREDENTIAL",
    "POSTCODE",
    "HOUSE_NUMBER",
    "HOUSE_NAME",
    "PAON",
    "UPRN",
    "USRN",
    "PROPERTY_ADDRESS",
)


def _container_with_drops(drops: list[str], command: list[str] | None = None) -> dict:
    return {
        "Config": {
            "CreateCommand": (
                command
                if command is not None
                else ["podman", "create", "--cap-drop", "all", "image"]
            ),
        },
        "HostConfig": {"CapAdd": [], "CapDrop": drops},
    }


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_rejects_rootful_podman(validator) -> None:
    assert validator._is_rootless({"host": {"security": {"rootless": False}}}) is False


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_accepts_both_rootless_info_schemas(validator) -> None:
    assert validator._is_rootless({"host": {"security": {"rootless": True}}}) is True
    assert validator._is_rootless({"Host": {"Security": {"Rootless": True}}}) is True


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_rejects_missing_or_conflicting_rootless_status(validator) -> None:
    assert validator._is_rootless({}) is False
    assert (
        validator._is_rootless(
            {
                "host": {"security": {"rootless": True}},
                "Host": {"Security": {"Rootless": False}},
            }
        )
        is False
    )


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_rejects_partial_capability_drop(validator) -> None:
    partial = _container_with_drops(["CAP_CHOWN", "CAP_NET_RAW"])

    with pytest.raises(RuntimeError, match="complete rootless capability drop set"):
        validator._require_cap_drop_all("partial", partial, ROOTLESS_CAPABILITIES)


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_requires_create_command_cap_drop_all(validator) -> None:
    full_report = _container_with_drops(
        ["ALL"],
        command=["podman", "create", "--cap-drop", "NET_RAW", "image"],
    )

    with pytest.raises(RuntimeError, match="not created with --cap-drop all"):
        validator._require_cap_drop_all(
            "wrong-command", full_report, ROOTLESS_CAPABILITIES
        )


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_accepts_all_sentinel_and_expanded_drop_set(validator) -> None:
    validator._require_cap_drop_all(
        "sentinel", _container_with_drops(["ALL"]), ROOTLESS_CAPABILITIES
    )

    expanded_runtime = ROOTLESS_CAPABILITIES | {
        "AUDIT_WRITE",
        "MKNOD",
        "NET_RAW",
        "FUTURE_CONCRETE_CAPABILITY",
    }
    validator._require_cap_drop_all(
        "expanded-runtime",
        _container_with_drops([f"CAP_{name}" for name in expanded_runtime]),
        expanded_runtime,
    )
    expanded = [f"CAP_{name}" for name in ROOTLESS_CAPABILITIES]
    validator._require_cap_drop_all(
        "expanded",
        _container_with_drops(
            expanded,
            command=["podman", "create", "--cap-drop=ALL", "image"],
        ),
        ROOTLESS_CAPABILITIES,
    )


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_uses_rootless_engine_capability_universe(validator) -> None:
    actual = ",".join(f"CAP_{name}" for name in sorted(ROOTLESS_CAPABILITIES))
    assert (
        validator._rootless_capabilities(
            {"host": {"security": {"capabilities": actual}}}
        )
        == ROOTLESS_CAPABILITIES
    )
    assert (
        validator._rootless_capabilities(
            {
                "Host": {
                    "Security": {
                        "Capabilities": [
                            name.casefold() for name in ROOTLESS_CAPABILITIES
                        ]
                    }
                }
            }
        )
        == ROOTLESS_CAPABILITIES
    )


@pytest.mark.parametrize("validator", VALIDATORS)
@pytest.mark.parametrize(
    "info",
    [
        {},
        {"host": {"security": {"capabilities": 7}}},
        {"host": {"security": {"capabilities": ["CAP_CHOWN", 7]}}},
        {"host": {"security": {"capabilities": "CAP_CHOWN,"}}},
        {"host": {"security": {"capabilities": "ALL"}}},
        {"host": {"security": {"capabilities": "CAP_ALL"}}},
        {"host": {"security": {"capabilities": "CAP_CHOWN;CAP_SETUID"}}},
    ],
)
def test_validator_rejects_missing_or_malformed_capability_universe(
    validator, info
) -> None:
    with pytest.raises(RuntimeError):
        validator._rootless_capabilities(info)


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_rejects_conflicting_capability_schemas(validator) -> None:
    with pytest.raises(RuntimeError, match="conflicting"):
        validator._rootless_capabilities(
            {
                "host": {"security": {"capabilities": "CAP_CHOWN"}},
                "Host": {"Security": {"Capabilities": "CAP_SETUID"}},
            }
        )


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_rejects_missing_advertised_capability(validator) -> None:
    missing_one = ROOTLESS_CAPABILITIES - {"SETUID"}
    drops = [f"CAP_{name}" for name in missing_one | {"NET_RAW"}]
    with pytest.raises(RuntimeError, match="complete rootless capability drop set"):
        validator._require_cap_drop_all(
            "missing-setuid", _container_with_drops(drops), ROOTLESS_CAPABILITIES
        )


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_rejects_empty_drop_for_nonempty_universe(validator) -> None:
    with pytest.raises(RuntimeError, match="complete rootless capability drop set"):
        validator._require_cap_drop_all(
            "empty-drop", _container_with_drops([]), ROOTLESS_CAPABILITIES
        )


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_accepts_explicitly_empty_capability_universe(validator) -> None:
    info = {"host": {"security": {"capabilities": ""}}}
    available = validator._rootless_capabilities(info)
    assert available == frozenset()
    validator._require_cap_drop_all(
        "already-empty", _container_with_drops([]), available
    )


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_rejects_capability_addition(validator) -> None:
    container = _container_with_drops(["ALL"])
    container["HostConfig"]["CapAdd"] = ["CAP_NET_ADMIN"]
    with pytest.raises(RuntimeError, match="adds Linux capabilities"):
        validator._require_cap_drop_all(
            "added-capability", container, ROOTLESS_CAPABILITIES
        )


@pytest.mark.parametrize("validator", VALIDATORS)
@pytest.mark.parametrize("cap_add", [None, "", "CAP_NET_ADMIN"])
def test_validator_rejects_malformed_capability_additions(validator, cap_add) -> None:
    container = _container_with_drops(["ALL"])
    container["HostConfig"]["CapAdd"] = cap_add
    with pytest.raises(RuntimeError, match="malformed added capabilities"):
        validator._require_cap_drop_all(
            "malformed-cap-add", container, ROOTLESS_CAPABILITIES
        )


@pytest.mark.parametrize("validator", VALIDATORS)
@pytest.mark.parametrize("cap_drop", [None, "ALL", ["CAP_CHOWN", 7], ["CAP_CHOWN,"]])
def test_validator_rejects_malformed_capability_drops(validator, cap_drop) -> None:
    container = _container_with_drops([])
    container["HostConfig"]["CapDrop"] = cap_drop
    with pytest.raises(RuntimeError, match="malformed dropped capabilities"):
        validator._require_cap_drop_all(
            "malformed-cap-drop", container, ROOTLESS_CAPABILITIES
        )


@pytest.mark.parametrize("validator", VALIDATORS)
@pytest.mark.parametrize(
    "field",
    [
        "PidMode",
        "IpcMode",
        "UsernsMode",
        "UTSMode",
        "CgroupnsMode",
        "CgroupMode",
    ],
)
def test_validator_rejects_host_namespace(validator, field: str) -> None:
    with pytest.raises(RuntimeError, match="joins host namespaces"):
        validator._require_no_host_namespaces("unsafe", {"HostConfig": {field: "host"}})


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_allows_private_or_container_namespace(validator) -> None:
    validator._require_no_host_namespaces(
        "contained",
        {
            "HostConfig": {
                "PidMode": "private",
                "IpcMode": "container:infra-id",
                "UsernsMode": "keep-id",
                "UTSMode": "container:infra-id",
                "CgroupnsMode": "private",
            }
        },
    )


def test_live_validator_rejects_wrong_or_mutable_image_identity() -> None:
    actual = "a" * 64
    container = {"Image": f"sha256:{actual}"}

    assert live._require_expected_image("runner", container, actual) == (
        f"sha256:{actual}"
    )
    with pytest.raises(RuntimeError, match="does not match"):
        live._require_expected_image("runner", container, "b" * 64)
    with pytest.raises(RuntimeError, match="full immutable SHA-256"):
        live._require_expected_image("runner", container, "candidate:latest")


def test_offline_validator_rejects_wrong_or_mutable_image_identity() -> None:
    actual = "a" * 64
    container = {"Image": f"sha256:{actual}"}

    assert offline._require_expected_image("ha", container, actual) == (
        f"sha256:{actual}"
    )
    with pytest.raises(RuntimeError, match="does not match"):
        offline._require_expected_image("ha", container, "b" * 64)
    with pytest.raises(RuntimeError, match="full immutable SHA-256"):
        offline._require_expected_image("ha", container, "candidate:latest")


def test_offline_validator_binds_exact_entrypoint_and_arguments() -> None:
    reviewed = {
        "Path": "python3",
        "Args": ["/workspace/tests/disposable_ha/offline_runner.py", "success"],
    }
    expected = offline._process_sha256(reviewed)

    assert offline._require_expected_process("runner", reviewed, expected) == expected
    with pytest.raises(RuntimeError, match="entrypoint or arguments"):
        offline._require_expected_process(
            "runner",
            {**reviewed, "Args": [*reviewed["Args"], "unexpected"]},
            expected,
        )
    with pytest.raises(RuntimeError, match="full SHA-256"):
        offline._require_expected_process("runner", reviewed, "reviewed-command")


def test_live_validator_binds_selenium_entrypoint_and_arguments_by_digest() -> None:
    image = {
        "Config": {
            "Entrypoint": ["/opt/bin/entry_point.sh"],
            "Cmd": ["--selenium-manager", "false"],
        }
    }
    reviewed = {
        "Path": "/opt/bin/entry_point.sh",
        "Args": ["--selenium-manager", "false"],
    }
    expected = live._reviewed_image_process_sha256(image)

    assert live._require_expected_process("selenium", reviewed, expected) == expected
    with pytest.raises(RuntimeError, match="entrypoint or arguments"):
        live._require_expected_process(
            "selenium",
            {**reviewed, "Args": [*reviewed["Args"], "unexpected"]},
            expected,
        )
    with pytest.raises(RuntimeError, match="full SHA-256"):
        live._require_expected_process("selenium", reviewed, "reviewed-command")


def test_live_validator_normalizes_podman_cmd_only_process_metadata() -> None:
    command = "/opt/bin/entry_point.sh"
    image = {"Config": {"Entrypoint": None, "Cmd": [command]}}
    podman_inspect = {"Path": command, "Args": [command]}

    expected = live._process_sha256(podman_inspect)

    assert live._reviewed_image_process_sha256(image) == expected
    assert (
        live._require_expected_process("selenium", podman_inspect, expected)
        == expected
    )


@pytest.mark.parametrize(
    "image",
    [
        {"Config": {}},
        {"Config": {"Entrypoint": [""], "Cmd": []}},
        {"Config": {"Entrypoint": "entry-point.sh", "Cmd": []}},
    ],
)
def test_live_validator_rejects_missing_or_malformed_image_process(image) -> None:
    with pytest.raises(RuntimeError, match="reviewed Selenium image"):
        live._reviewed_image_process_sha256(image)


@pytest.mark.parametrize("validator", VALIDATORS)
@pytest.mark.parametrize("environment_name", SENSITIVE_ENVIRONMENT_NAMES)
def test_validator_rejects_added_sensitive_environment_variable(
    validator, environment_name: str
) -> None:
    container = {
        "Config": {
            "Env": ["PATH=/usr/bin", f"{environment_name}=must-not-enter-container"]
        }
    }
    image = {"Config": {"Env": ["PATH=/usr/bin"]}}

    with pytest.raises(RuntimeError, match="sensitive environment override"):
        validator._require_no_sensitive_environment_overrides(
            "application", container, image
        )


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_rejects_changed_sensitive_base_image_environment(validator) -> None:
    container = {
        "Config": {"Env": ["PATH=/usr/bin", "SE_VNC_PASSWORD=host-supplied-secret"]}
    }
    image = {"Config": {"Env": ["PATH=/usr/bin", "SE_VNC_PASSWORD=reviewed-default"]}}

    with pytest.raises(RuntimeError, match="SE_VNC_PASSWORD"):
        validator._require_no_sensitive_environment_overrides(
            "application", container, image
        )


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_rejects_malformed_sensitive_environment_entry(validator) -> None:
    container = {"Config": {"Env": ["PATH=/usr/bin", "HA_TOKEN"]}}
    image = {"Config": {"Env": ["PATH=/usr/bin"]}}

    with pytest.raises(RuntimeError, match="HA_TOKEN"):
        validator._require_no_sensitive_environment_overrides(
            "application", container, image
        )


@pytest.mark.parametrize("validator", VALIDATORS)
def test_validator_allows_unchanged_reviewed_base_image_environment(validator) -> None:
    container = {
        "Config": {
            "Env": [
                "PATH=/usr/bin",
                "SE_VNC_PASSWORD=reviewed-default",
                "NORMAL_RUNTIME_SETTING=enabled",
            ]
        }
    }
    image = {"Config": {"Env": ["PATH=/usr/bin", "SE_VNC_PASSWORD=reviewed-default"]}}

    validator._require_no_sensitive_environment_overrides(
        "application", container, image
    )


def test_offline_expected_mappings_require_every_container_exactly_once() -> None:
    assert offline._parse_name_mapping(
        [f"ha={'a' * 64}", f"runner={'b' * 64}"],
        {"ha", "runner"},
        "expected images",
    ) == {"ha": "a" * 64, "runner": "b" * 64}

    with pytest.raises(RuntimeError, match="membership mismatch"):
        offline._parse_name_mapping(
            [f"ha={'a' * 64}"], {"ha", "runner"}, "expected images"
        )
    with pytest.raises(RuntimeError, match="duplicate"):
        offline._parse_name_mapping(
            [f"ha={'a' * 64}", f"ha={'b' * 64}"],
            {"ha"},
            "expected images",
        )


@pytest.mark.parametrize(
    ("name", "container", "expected"),
    [
        (
            "runner",
            {
                "Path": "python3",
                "Args": [
                    "/opt/ukbcd/live_canary_runner.py",
                    "--confirm-one-public-fixture-lookup",
                ],
            },
            live.RUNNER_PROCESS,
        ),
        (
            "proxy",
            {
                "Path": "python3",
                "Args": [
                    "/opt/ukbcd/live_allowlist_proxy.py",
                    "--max-requests",
                    "256",
                    "--minimum-interval-ms",
                    "0",
                ],
            },
            live.PROXY_PROCESS,
        ),
    ],
)
def test_live_validator_rejects_wrong_payload_or_arguments(
    name: str,
    container: dict,
    expected: tuple[str, tuple[str, ...]],
) -> None:
    with pytest.raises(RuntimeError, match="entrypoint or arguments"):
        live._require_exact_process(name, container, expected)


def test_live_validator_accepts_exact_runner_and_proxy_processes() -> None:
    live._require_exact_process(
        "runner",
        {"Path": live.RUNNER_PROCESS[0], "Args": list(live.RUNNER_PROCESS[1])},
        live.RUNNER_PROCESS,
    )
    live._require_exact_process(
        "proxy",
        {"Path": live.PROXY_PROCESS[0], "Args": list(live.PROXY_PROCESS[1])},
        live.PROXY_PROCESS,
    )


def test_offline_pod_members_come_from_inspect() -> None:
    pod = {
        "Containers": [
            {"Id": "infra-id", "Name": "infra"},
            {"Id": "runner-id", "Name": "runner"},
        ]
    }

    assert offline._pod_members(pod) == {"infra", "runner"}
    offline._require_exact_members(
        "offline-pod", offline._pod_members(pod), {"infra", "runner"}
    )


@pytest.mark.parametrize(
    ("actual", "expected"),
    [
        ({"infra", "runner", "unexpected"}, {"infra", "runner"}),
        ({"infra"}, {"infra", "runner"}),
    ],
)
def test_offline_pod_rejects_extra_or_missing_member(
    actual: set[str], expected: set[str]
) -> None:
    with pytest.raises(RuntimeError, match="membership mismatch"):
        offline._require_exact_members("offline-pod", actual, expected)


def test_live_network_members_come_from_network_inspect() -> None:
    network = {
        "containers": {
            "runner-id": {"name": "runner"},
            "selenium-id": {"name": "selenium"},
            "proxy-id": {"name": "proxy"},
        }
    }

    actual = live._network_members(network)
    assert actual == {"runner", "selenium", "proxy"}
    live._require_exact_members(
        "internal-network", actual, {"runner", "selenium", "proxy"}
    )


def test_live_planned_members_scan_every_unstarted_container(monkeypatch) -> None:
    containers = {
        "runner": {"NetworkSettings": {"Networks": {"internal": {}}}},
        "selenium": {"NetworkSettings": {"Networks": {"internal": {}}}},
        "proxy": {
            "NetworkSettings": {"Networks": {"internal": {}, "egress": {}}}
        },
        "unrelated": {"NetworkSettings": {"Networks": {"other": {}}}},
    }
    monkeypatch.setattr(live, "_all_container_names", lambda: set(containers))
    monkeypatch.setattr(live, "_inspect_container", containers.__getitem__)

    assert live._planned_network_members("internal") == {
        "runner",
        "selenium",
        "proxy",
    }
    assert live._planned_network_members("egress") == {"proxy"}


def test_live_accepts_empty_runtime_members_for_exact_unstarted_plan(
    monkeypatch,
) -> None:
    expected = {"runner", "selenium", "proxy"}
    monkeypatch.setattr(live, "_planned_network_members", lambda name: expected)

    planned, reported, source = live._validated_network_members(
        "internal", {"containers": {}}, expected
    )

    assert planned == expected
    assert reported == set()
    assert source == "all-container-inspect-unstarted-intent"


def test_live_rejects_extra_unstarted_member_when_runtime_map_is_empty(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        live,
        "_planned_network_members",
        lambda name: {"runner", "selenium", "proxy", "unexpected"},
    )

    with pytest.raises(RuntimeError, match="membership mismatch"):
        live._validated_network_members(
            "internal",
            {"containers": {}},
            {"runner", "selenium", "proxy"},
        )


def test_live_rejects_runtime_membership_that_disagrees_with_the_plan(
    monkeypatch,
) -> None:
    expected = {"runner", "selenium", "proxy"}
    monkeypatch.setattr(live, "_planned_network_members", lambda name: expected)
    network = {
        "containers": {
            "runner-id": {"name": "runner"},
            "selenium-id": {"name": "selenium"},
        }
    }

    with pytest.raises(RuntimeError, match="membership mismatch"):
        live._validated_network_members("internal", network, expected)


@pytest.mark.parametrize(
    ("network", "expected"),
    [
        (
            {
                "containers": {
                    "proxy-id": {"name": "proxy"},
                    "unexpected-id": {"name": "unexpected"},
                }
            },
            {"proxy"},
        ),
        ({"containers": {}}, {"proxy"}),
    ],
)
def test_live_network_rejects_extra_or_missing_member(
    network: dict, expected: set[str]
) -> None:
    with pytest.raises(RuntimeError, match="membership mismatch"):
        live._require_exact_members(
            "egress-network", live._network_members(network), expected
        )
