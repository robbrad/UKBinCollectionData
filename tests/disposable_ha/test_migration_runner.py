"""Unit tests for disposable Home Assistant migration validation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_RUNNER_PATH = Path(__file__).with_name("migration_runner.py")
_RUNNER_SPEC = importlib.util.spec_from_file_location(
    "ukbcd_disposable_migration_runner", _RUNNER_PATH
)
assert _RUNNER_SPEC is not None and _RUNNER_SPEC.loader is not None
migration_runner = importlib.util.module_from_spec(_RUNNER_SPEC)
_RUNNER_SPEC.loader.exec_module(migration_runner)


def _expected_entity_ids() -> set[str]:
    return {
        f"{entry_id}_{suffix}"
        for entry_id in migration_runner.ENTRY_IDS
        for suffix in migration_runner.EXPECTED_ENTITY_SUFFIXES
    }


def test_entity_contract_accepts_all_existing_sensor_and_calendar_ids(
    monkeypatch,
) -> None:
    expected = _expected_entity_ids()
    monkeypatch.setattr(migration_runner, "_entity_ids", lambda: expected)

    assert migration_runner._assert_entity_contract(0.1) == 24


@pytest.mark.parametrize(
    "missing_suffix",
    (
        "Fixture Bin",
        "Fixture Bin_calendar",
        "Fixture Bin_next_collection_date",
        "raw_json",
    ),
)
def test_entity_contract_rejects_a_missing_existing_identity(
    monkeypatch, missing_suffix: str
) -> None:
    expected = _expected_entity_ids()
    expected.remove(f"{migration_runner.ENTRY_IDS[0]}_{missing_suffix}")
    monkeypatch.setattr(migration_runner, "_entity_ids", lambda: expected)

    with pytest.raises(RuntimeError, match="identity contract"):
        migration_runner._assert_entity_contract(0)
