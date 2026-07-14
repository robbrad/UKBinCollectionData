"""Unit tests for disposable Home Assistant result validation."""

from __future__ import annotations

import pytest

from tests.disposable_ha import offline_runner


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
