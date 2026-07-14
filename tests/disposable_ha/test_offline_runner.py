"""Unit tests for disposable Home Assistant result validation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


# Some Home Assistant dependencies install an unrelated top-level ``tests``
# package.  Load the sibling runner directly so this isolated harness test does
# not depend on site-packages ordering.
_RUNNER_PATH = Path(__file__).with_name("offline_runner.py")
_RUNNER_SPEC = importlib.util.spec_from_file_location(
    "ukbcd_disposable_offline_runner", _RUNNER_PATH
)
assert _RUNNER_SPEC is not None and _RUNNER_SPEC.loader is not None
offline_runner = importlib.util.module_from_spec(_RUNNER_SPEC)
_RUNNER_SPEC.loader.exec_module(offline_runner)


def test_session_cleanup_accepts_empty_selenium_status_slots(monkeypatch) -> None:
    monkeypatch.setattr(
        offline_runner,
        "_wait_for_url",
        lambda url, timeout: {
            "value": {
                "ready": True,
                "nodes": [
                    {
                        "slots": [
                            {"session": None},
                            {"session": None},
                        ]
                    }
                ],
            }
        },
    )

    offline_runner._assert_no_selenium_sessions()


def test_session_cleanup_rejects_an_active_selenium_slot(monkeypatch) -> None:
    monkeypatch.setattr(
        offline_runner,
        "_wait_for_url",
        lambda url, timeout: {
            "value": {
                "ready": True,
                "nodes": [
                    {"slots": [{"session": {"sessionId": "synthetic"}}]}
                ],
            }
        },
    )

    with pytest.raises(RuntimeError, match="remained active"):
        offline_runner._assert_no_selenium_sessions()


@pytest.mark.parametrize(
    "status",
    (
        None,
        {},
        {"value": {"ready": False, "nodes": []}},
        {"value": {"ready": True, "nodes": [{"slots": None}]}},
    ),
)
def test_session_cleanup_rejects_malformed_status(monkeypatch, status) -> None:
    monkeypatch.setattr(
        offline_runner,
        "_wait_for_url",
        lambda url, timeout: status,
    )

    with pytest.raises(RuntimeError, match="invalid"):
        offline_runner._assert_no_selenium_sessions()
