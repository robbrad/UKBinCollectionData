"""Verify actual HA config-entry migration and restart persistence offline."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, quote_plus

CONFIG = Path("/config")
EVIDENCE = Path(os.environ.get("UKBCD_TEST_EVIDENCE_DIR", "/evidence"))
HA_VERSION = "2026.7.2"
ENTRY_IDS = (
    "ddddddddddddddddddddddddddddddd1",
    "ddddddddddddddddddddddddddddddd2",
    "ddddddddddddddddddddddddddddddd3",
)
EXPECTED_ENTITY_SUFFIXES = (
    "Fixture Bin",
    "Fixture Bin_bin_type",
    "Fixture Bin_calendar",
    "Fixture Bin_colour",
    "Fixture Bin_days_until_collection",
    "Fixture Bin_next_collection_date",
    "Fixture Bin_next_collection_human_readable",
    "raw_json",
)
SNAPSHOT_PATH = EVIDENCE / "migration_v4_snapshot.json"
SENSITIVE_SENTINELS = (
    "Synthetic Address V1",
    "Synthetic Address V2",
    "Synthetic Address V3",
    "Ignored legacy house value",
    "Ignored legacy PAON value",
)

COMMON_DATA = {
    "council": "FixtureCouncil",
    "url": "http://127.0.0.1:8081/static",
    "timeout": 75,
    "icon_color_mapping": "{}",
}
EXPECTED_DATA = {
    ENTRY_IDS[0]: {
        **COMMON_DATA,
        "name": "Offline migration v1",
        "update_interval": 12,
        "manual_refresh_only": True,
        "number": "Synthetic Address V1",
        "web_driver": "http://127.0.0.1:4444",
        "headless": True,
        "local_browser": False,
        "skip_get_url": True,
    },
    ENTRY_IDS[1]: {
        **COMMON_DATA,
        "name": "Offline migration v2",
        "update_interval": 6,
        "manual_refresh_only": True,
        "number": "Synthetic Address V2",
        "web_driver": "http://127.0.0.1:4444/wd/hub",
        "headless": False,
        "local_browser": True,
        "skip_get_url": True,
    },
    ENTRY_IDS[2]: {
        **COMMON_DATA,
        "name": "Offline migration v3",
        "update_interval": 12,
        "manual_refresh_only": True,
        "number": "Synthetic Address V3",
        "web_driver": "http://127.0.0.1:4444",
        "headless": True,
        "local_browser": False,
        "skip_get_url": True,
    },
}


def _wait_for_file(path: Path, timeout: float) -> Path:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file() and path.stat().st_size:
            return path
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for disposable file: {path.name}")


def _network_assertions() -> tuple[list[str], int]:
    interfaces = sorted(path.name for path in Path("/sys/class/net").iterdir())
    routes = Path("/proc/net/route").read_text(encoding="utf-8")
    rows = [line.split() for line in routes.splitlines()[1:] if line.split()]
    default_routes = [row for row in rows if len(row) > 1 and row[1] == "00000000"]
    if interfaces != ["lo"] or default_routes:
        raise RuntimeError(
            f"Offline network assertion failed: interfaces={interfaces}, "
            f"default_routes={default_routes}"
        )
    return interfaces, len(default_routes)


def _load_entry_projection() -> dict[str, dict]:
    storage = json.loads(
        _wait_for_file(CONFIG / ".storage" / "core.config_entries", 15).read_text(
            encoding="utf-8"
        )
    )
    return {
        entry["entry_id"]: {"version": entry["version"], "data": entry["data"]}
        for entry in storage["data"]["entries"]
        if entry.get("entry_id") in ENTRY_IDS
    }


def _expected_projection() -> dict[str, dict]:
    return {
        entry_id: {"version": 4, "data": data}
        for entry_id, data in EXPECTED_DATA.items()
    }


def _wait_for_projection(timeout: float) -> dict[str, dict]:
    expected = _expected_projection()
    deadline = time.monotonic() + timeout
    projection: dict[str, dict] = {}
    while time.monotonic() < deadline:
        try:
            projection = _load_entry_projection()
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
        if projection == expected:
            return projection
        time.sleep(0.5)
    raise RuntimeError(
        "Persisted config entries did not match the exact v4 migration contract: "
        f"observed_entry_ids={sorted(projection)}"
    )


def _scrape_count() -> int:
    path = EVIDENCE / "non_selenium_scrape_calls"
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8").splitlines())


def _wait_for_scrape_count(expected: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _scrape_count() >= expected:
            time.sleep(2)
            observed = _scrape_count()
            if observed != expected:
                raise RuntimeError(
                    f"Expected {expected} fixture scrapes, observed {observed}"
                )
            return
        time.sleep(0.5)
    raise RuntimeError(
        f"Timed out waiting for {expected} fixture scrapes; observed {_scrape_count()}"
    )


def _entry_setup_markers() -> tuple[str, ...]:
    return tuple(
        f"async_setup_entry finished for entry_id={entry_id}" for entry_id in ENTRY_IDS
    )


def _wait_for_first_log(timeout: float) -> bytes:
    path = CONFIG / "home-assistant.log"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            content = path.read_bytes()
            text = content.decode("utf-8", errors="replace")
            if all(marker in text for marker in _entry_setup_markers()):
                return content
        time.sleep(0.5)
    raise RuntimeError("Timed out waiting for first-boot HA setup markers")


def _wait_for_restart_log(snapshot: dict, timeout: float) -> bytes:
    """Return only log bytes written after the first validated boot when possible."""
    path = CONFIG / "home-assistant.log"
    prefix_size = snapshot["first_log_size"]
    prefix_sha256 = snapshot["first_log_sha256"]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            content = path.read_bytes()
            if (
                len(content) >= prefix_size
                and hashlib.sha256(content[:prefix_size]).hexdigest() == prefix_sha256
            ):
                current_boot = content[prefix_size:]
            else:
                # HA may rotate or recreate its log on restart.  In that case the
                # current file is the second boot's log and is safe to inspect whole.
                current_boot = content
            text = current_boot.decode("utf-8", errors="replace")
            if all(marker in text for marker in _entry_setup_markers()):
                return current_boot
        time.sleep(0.5)
    raise RuntimeError("Timed out waiting for second-boot HA setup markers")


def _entity_ids() -> set[str | None]:
    storage = json.loads(
        _wait_for_file(CONFIG / ".storage" / "core.entity_registry", 30).read_text(
            encoding="utf-8"
        )
    )
    return {
        entity.get("unique_id")
        for entity in storage["data"].get("entities", [])
        if entity.get("platform") == "uk_bin_collection"
        and any(
            str(entity.get("unique_id", "")).startswith(entry_id)
            for entry_id in ENTRY_IDS
        )
    }


def _assert_entity_contract(timeout: float) -> int:
    expected = {
        f"{entry_id}_{suffix}"
        for entry_id in ENTRY_IDS
        for suffix in EXPECTED_ENTITY_SUFFIXES
    }
    deadline = time.monotonic() + timeout
    actual: set[str | None] = set()
    while time.monotonic() < deadline:
        try:
            actual = _entity_ids()
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
        if actual == expected:
            return len(actual)
        time.sleep(0.5)
    raise RuntimeError(
        "Migrated entries did not retain the exact sensor/calendar identity contract"
    )


def _redaction_variants() -> set[str]:
    variants: set[str] = set()
    for value in SENSITIVE_SENTINELS:
        variants.update(
            (value, "".join(value.split()), quote(value), quote_plus(value))
        )
    return {value for value in variants if value}


def _write_redacted_log(log_bytes: bytes, phase: str) -> None:
    text = log_bytes.decode("utf-8", errors="replace")
    redacted = text
    leaked: list[str] = []
    for value in sorted(_redaction_variants(), key=len, reverse=True):
        if value.casefold() in text.casefold():
            leaked.append(value)
        redacted = re.sub(re.escape(value), "[REDACTED]", redacted, flags=re.IGNORECASE)
    (EVIDENCE / f"migration_{phase}.redacted.log").write_text(
        redacted, encoding="utf-8"
    )
    if leaked:
        raise RuntimeError("HA migration log contains a synthetic address sentinel")


def _runtime_contract() -> tuple[str, str, str]:
    ha_version = importlib.metadata.version("homeassistant")
    core_version = importlib.metadata.version("uk-bin-collection")
    if ha_version != HA_VERSION or sys.version_info[:2] != (3, 14):
        raise RuntimeError("The disposable runtime is not HA 2026.7.2/Python 3.14")
    return ha_version, sys.version, core_version


def _run(phase: str, timeout: float) -> dict:
    interfaces, default_route_count = _network_assertions()
    expected_scrapes = 3 if phase == "first" else 6
    _wait_for_scrape_count(expected_scrapes, timeout)
    projection = _wait_for_projection(timeout)
    projection_sha256 = hashlib.sha256(
        json.dumps(projection, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    entity_count = _assert_entity_contract(timeout)

    if phase == "first":
        log_bytes = _wait_for_first_log(timeout)
        log_text = log_bytes.decode("utf-8", errors="replace")
        for entry_id in ENTRY_IDS:
            marker = f"Migrated config entry {entry_id} to version 4"
            if log_text.count(marker) != 1:
                raise RuntimeError(
                    f"Expected one first-boot migration marker for {entry_id}"
                )
        snapshot = {
            "projection": projection,
            "first_log_size": len(log_bytes),
            "first_log_sha256": hashlib.sha256(log_bytes).hexdigest(),
        }
        SNAPSHOT_PATH.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8"
        )
        migration_reran = False
    else:
        snapshot = json.loads(
            _wait_for_file(SNAPSHOT_PATH, 10).read_text(encoding="utf-8")
        )
        if projection != snapshot["projection"]:
            raise RuntimeError("The v4 config-entry projection changed across restart")
        log_bytes = _wait_for_restart_log(snapshot, timeout)
        log_text = log_bytes.decode("utf-8", errors="replace")
        migration_reran = "Migrated config entry" in log_text
        if migration_reran:
            raise RuntimeError("A persisted v4 entry was migrated again after restart")

    integration_errors = [
        line
        for line in log_text.splitlines()
        if "ERROR" in line and "[custom_components.uk_bin_collection]" in line
    ]
    if integration_errors or "Unexpected coordinator error" in log_text:
        raise RuntimeError("Home Assistant logged an unexpected migration/setup error")
    _write_redacted_log(log_bytes, phase)
    ha_version, python_version, core_version = _runtime_contract()
    return {
        "network_interfaces": interfaces,
        "default_route_count": default_route_count,
        "home_assistant_version": ha_version,
        "python_version": python_version,
        "core_package_version": core_version,
        "checks": {
            "source_versions": [1, 2, 3],
            "persisted_target_version": 4,
            "persisted_entry_count": len(projection),
            "registered_entity_count": entity_count,
            "fixture_scrape_calls": expected_scrapes,
            "legacy_aliases_absent": True,
            "boolean_fields_are_boolean": True,
            "persisted_projection_sha256": projection_sha256,
            "migration_reran_after_restart": migration_reran,
            "projection_preserved_across_restart": phase == "restart",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("first", "restart"), required=True)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    report = {"phase": args.phase, "status": "failed"}
    try:
        report.update(_run(args.phase, args.timeout))
        report["status"] = "passed"
    except Exception as exc:
        report["failure_type"] = type(exc).__name__
        report["failure_message"] = str(exc)
        raise
    finally:
        (EVIDENCE / f"migration_{args.phase}_report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
