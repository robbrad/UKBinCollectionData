"""Tests for the candidate image's offline dependency-closure verifier."""

from tests.disposable_ha.verify_runtime_requirements import dependency_errors


def test_runtime_verifier_reports_missing_root_distribution() -> None:
    assert dependency_errors("ukbcd-definitely-not-installed-7f930b9a") == [
        "missing distribution: ukbcd-definitely-not-installed-7f930b9a"
    ]
