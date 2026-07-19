"""Validate an offline HA run from a sibling container in the same pod."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, quote_plus
from urllib.request import urlopen

CONFIG = Path("/config")
EVIDENCE = Path(os.environ.get("UKBCD_TEST_EVIDENCE_DIR", "/evidence"))
HA_VERSION = "2026.7.2"
REPAIR_PERSIST_TIMEOUT = 210
SUCCESS_ENTRY_ID = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
CONTROL_ENTRY_ID = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
COLLISION_ENTRY_ID = "cccccccccccccccccccccccccccccccc"
SENSITIVE_VALUES = ("ZZ99 9ZZ", "Codex Test House")


def _wait_for_url(url: str, timeout: float) -> dict | str:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as response:  # noqa: S310 - loopback only
                body = response.read().decode("utf-8")
                if response.status == 200:
                    try:
                        return json.loads(body)
                    except json.JSONDecodeError:
                        return body
        except Exception as exc:  # service may still be starting
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(
        f"Timed out waiting for loopback service: {type(last_error).__name__}"
    )


def _wait_for_log(markers: tuple[str, ...], timeout: float) -> str:
    log_path = CONFIG / "home-assistant.log"
    deadline = time.monotonic() + timeout
    text = ""
    while time.monotonic() < deadline:
        if log_path.exists():
            text = log_path.read_text(encoding="utf-8", errors="replace")
            if all(marker in text for marker in markers):
                return text
        time.sleep(1)
    raise RuntimeError(f"Missing HA log markers: {markers!r}")


def _wait_for_file(path: Path, timeout: float) -> Path:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file() and path.stat().st_size:
            return path
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for disposable storage file: {path.name}")


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8").splitlines())


def _read_requests() -> list[dict]:
    path = _wait_for_file(EVIDENCE / "fixture_requests.jsonl", 15)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _storage_data(name: str, timeout: float = 30) -> dict:
    path = _wait_for_file(CONFIG / ".storage" / name, timeout)
    return json.loads(path.read_text(encoding="utf-8"))["data"]


def _assert_entity_ids(expected: set[str]) -> int:
    deadline = time.monotonic() + 30
    actual: set[str | None] = set()
    while time.monotonic() < deadline:
        entities = _storage_data("core.entity_registry").get("entities", [])
        actual = {
            entity.get("unique_id")
            for entity in entities
            if entity.get("platform") == "uk_bin_collection"
        }
        if expected <= actual:
            return len(actual)
        time.sleep(0.5)
    missing = expected - actual
    raise RuntimeError(
        f"Expected sensor/calendar entities were not registered: {sorted(missing)}"
    )


def _assert_one_dependency_repair(timeout: float) -> None:
    expected_id = f"dependency_{COLLISION_ENTRY_ID}"
    # HA intentionally delays registry writes created during startup by 180
    # seconds.  Read the persisted registry only after that bounded delay; the
    # in-memory issue is already visible to the Repairs UI immediately.
    issues = _storage_data("repairs.issue_registry", timeout).get("issues", [])
    # Transient HA Repairs deliberately persist only their stable domain and
    # issue id; their translation metadata is regenerated in memory at startup.
    matches = [
        issue
        for issue in issues
        if issue.get("domain") == "uk_bin_collection"
        and issue.get("issue_id") == expected_id
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one structured dependency Repair, "
            f"observed {len(matches)}"
        )


def _redaction_variants() -> set[str]:
    variants: set[str] = set()
    for value in SENSITIVE_VALUES:
        variants.update(
            {
                value,
                "".join(value.split()),
                quote(value),
                quote_plus(value),
            }
        )
    return {value for value in variants if value}


def _write_redacted_ha_log(log_text: str) -> None:
    redacted = log_text
    leaked: list[str] = []
    for value in sorted(_redaction_variants(), key=len, reverse=True):
        if value.casefold() in log_text.casefold():
            leaked.append(value)
        redacted = re.sub(re.escape(value), "[REDACTED]", redacted, flags=re.IGNORECASE)
    (EVIDENCE / "home-assistant.redacted.log").write_text(redacted, encoding="utf-8")
    if leaked:
        raise RuntimeError("Home Assistant log contains a synthetic household sentinel")


def _assert_fixture_request_contract(mode: str) -> dict[str, int | bool]:
    requests = _read_requests()
    binday = [request for request in requests if request.get("path") == "/binday"]
    browser = [request for request in binday if request.get("browser")]
    direct = [request for request in binday if not request.get("browser")]
    if len(direct) != 1:
        raise RuntimeError(
            f"Expected one deliberate direct-HTTP /binday request, observed {len(direct)}"
        )
    if mode == "success":
        if len(browser) != 1:
            raise RuntimeError(
                "Expected exactly one browser /binday request; skip_get_url may be broken"
            )
        if not browser[0].get("custom_user_agent"):
            raise RuntimeError("The configured browser user agent was not propagated")
    elif browser:
        raise RuntimeError("The collision run created a browser session unexpectedly")
    return {
        "binday_browser_requests": len(browser),
        "binday_direct_requests": len(direct),
        "custom_user_agent_observed": bool(
            browser and browser[0].get("custom_user_agent")
        ),
    }


def _assert_no_selenium_sessions() -> None:
    # Selenium 4.45 removed the legacy GET /sessions route.  The supported
    # status payload exposes every node slot and its current session, which is
    # also a stronger cleanup assertion for a bounded one-node test grid.
    status = _wait_for_url("http://127.0.0.1:4444/status", 15)
    value = status.get("value") if isinstance(status, dict) else None
    nodes = value.get("nodes") if isinstance(value, dict) else None
    if not isinstance(nodes, list) or not value.get("ready"):
        raise RuntimeError("Selenium returned an invalid status payload")

    active_sessions = 0
    for node in nodes:
        slots = node.get("slots") if isinstance(node, dict) else None
        if not isinstance(slots, list):
            raise RuntimeError("Selenium returned an invalid node-slot payload")
        active_sessions += sum(
            1
            for slot in slots
            if not isinstance(slot, dict) or slot.get("session") is not None
        )

    if active_sessions:
        raise RuntimeError("A Selenium session remained active after the HA lookup")


def _network_assertions() -> tuple[list[str], list[list[str]]]:
    interfaces = sorted(path.name for path in Path("/sys/class/net").iterdir())
    routes = Path("/proc/net/route").read_text(encoding="utf-8")
    route_rows = [line.split() for line in routes.splitlines()[1:] if line.split()]
    default_routes = [
        row for row in route_rows if len(row) > 1 and row[1] == "00000000"
    ]
    if interfaces != ["lo"] or default_routes:
        raise RuntimeError(
            f"Offline network assertion failed: interfaces={interfaces}, "
            f"default_routes={default_routes}"
        )
    return interfaces, default_routes


def _run(mode: str, timeout: float) -> dict:
    interfaces, default_routes = _network_assertions()
    fixture_health = _wait_for_url("http://127.0.0.1:8081/health", 30)
    selenium_status = _wait_for_url("http://127.0.0.1:4444/status", 90)
    if not (
        isinstance(selenium_status, dict)
        and selenium_status.get("value", {}).get("ready")
    ):
        raise RuntimeError("Selenium status did not report ready")

    try:
        urlopen("http://127.0.0.1:8081/binday", timeout=3)  # noqa: S310
    except HTTPError as exc:
        direct_preflight_status = exc.code
    else:
        direct_preflight_status = 200
    if direct_preflight_status != 403:
        raise RuntimeError("The deterministic direct-HTTP denial was not reproduced")

    if mode == "success":
        markers = (
            "Initial data fetched successfully",
            "Setting up UK Bin Collection Data platform",
            "Setting up UK Bin Collection Calendar platform",
            "async_setup_entry finished",
        )
        _wait_for_log(markers, timeout)
        time.sleep(12)
        log_text = (CONFIG / "home-assistant.log").read_text(
            encoding="utf-8", errors="replace"
        )
        scrape_calls = _line_count(EVIDENCE / "south_kesteven_scrape_calls")
        if scrape_calls != 1:
            raise RuntimeError(f"Expected one initial scrape, observed {scrape_calls}")
        integration_errors = [
            line
            for line in log_text.splitlines()
            if "ERROR" in line and "[custom_components.uk_bin_collection]" in line
        ]
        if integration_errors or "Unexpected coordinator error" in log_text:
            raise RuntimeError("Home Assistant logged an unexpected integration error")
        entity_count = _assert_entity_ids(
            {
                f"{SUCCESS_ENTRY_ID}_Black Bin",
                f"{SUCCESS_ENTRY_ID}_Grey Bin",
                f"{SUCCESS_ENTRY_ID}_Black Bin_calendar",
                f"{SUCCESS_ENTRY_ID}_Grey Bin_calendar",
            }
        )
        checks = {
            "south_kesteven_scrape_calls": scrape_calls,
            "registered_entity_count": entity_count,
            "sensor_platform_marker": markers[1] in log_text,
            "calendar_platform_marker": markers[2] in log_text,
        }
    else:
        _wait_for_log(("A Python dependency is missing or shadowed",), timeout)
        time.sleep(12)
        log_text = (CONFIG / "home-assistant.log").read_text(
            encoding="utf-8", errors="replace"
        )
        non_selenium_calls = _line_count(EVIDENCE / "non_selenium_scrape_calls")
        collision_calls = _line_count(EVIDENCE / "south_kesteven_scrape_calls")
        if non_selenium_calls != 1:
            raise RuntimeError("The non-Selenium control entry did not remain isolated")
        if collision_calls != 1:
            raise RuntimeError("The collision entry retried unexpectedly")
        if (EVIDENCE / "ha_poison_executed").exists():
            raise RuntimeError("The top-level shadow package executed inside HA")
        _assert_one_dependency_repair(max(timeout, REPAIR_PERSIST_TIMEOUT))
        if "attempted relative import beyond top-level package" in log_text:
            raise RuntimeError("The raw relative-import failure escaped into HA")
        if "Unexpected coordinator error" in log_text:
            raise RuntimeError("The typed dependency error reached the generic handler")
        entity_count = _assert_entity_ids(
            {
                f"{CONTROL_ENTRY_ID}_Fixture Bin",
                f"{CONTROL_ENTRY_ID}_Fixture Bin_calendar",
            }
        )
        checks = {
            "non_selenium_scrape_calls": non_selenium_calls,
            "collision_entry_calls": collision_calls,
            "dependency_repair_persisted": True,
            "poison_module_not_executed": True,
            "registered_control_entity_count": entity_count,
            "raw_import_error_absent": True,
        }

    _assert_no_selenium_sessions()
    checks.update(_assert_fixture_request_contract(mode))
    _write_redacted_ha_log(log_text)

    home_assistant_version = importlib.metadata.version("homeassistant")
    if home_assistant_version != HA_VERSION or sys.version_info[:2] != (3, 14):
        raise RuntimeError(
            "The disposable runtime is not the accepted HA/Python version"
        )

    return {
        "network_interfaces": interfaces,
        "default_route_count": len(default_routes),
        "fixture_health": fixture_health,
        "selenium_ready": True,
        "selenium_sessions_after_lookup": 0,
        "direct_http_preflight_status": direct_preflight_status,
        "home_assistant_version": home_assistant_version,
        "python_version": sys.version,
        "core_package_version": importlib.metadata.version("uk-bin-collection"),
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("success", "collision"), required=True)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    report = {"mode": args.mode, "status": "failed"}
    try:
        report.update(_run(args.mode, args.timeout))
        report["status"] = "passed"
    except Exception as exc:
        report["failure_type"] = type(exc).__name__
        report["failure_message"] = str(exc)
        raise
    finally:
        (EVIDENCE / f"offline_{args.mode}_report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
