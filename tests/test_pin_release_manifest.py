"""Tests for fail-closed release-manifest pinning."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

from scripts import pin_release_manifest
from scripts.pin_release_manifest import pin_exact_requirement


def _write_release_files(tmp_path: Path, requirement: str) -> tuple[Path, Path]:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.poetry]\nname = "uk-bin-collection"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "domain": "uk_bin_collection",
                "version": "1.2.3",
                "requirements": [requirement],
            }
        ),
        encoding="utf-8",
    )
    return pyproject, manifest


def test_release_manifest_is_pinned_only_to_matching_core(tmp_path: Path) -> None:
    pyproject, manifest = _write_release_files(tmp_path, "uk-bin-collection>=1.2.3")

    assert (
        pin_exact_requirement("1.2.3", pyproject_path=pyproject, manifest_path=manifest)
        == []
    )
    assert json.loads(manifest.read_text(encoding="utf-8"))["requirements"] == [
        "uk-bin-collection==1.2.3"
    ]


def test_check_mode_does_not_mutate_manifest(tmp_path: Path) -> None:
    pyproject, manifest = _write_release_files(tmp_path, "uk-bin-collection>=1.2.3")
    before = manifest.read_bytes()

    assert (
        pin_exact_requirement(
            "1.2.3",
            pyproject_path=pyproject,
            manifest_path=manifest,
            check_only=True,
        )
        == []
    )
    assert manifest.read_bytes() == before


def test_pin_refuses_version_mismatch_or_unrelated_requirements(
    tmp_path: Path,
) -> None:
    pyproject, manifest = _write_release_files(tmp_path, "other-package==1.2.3")
    before = manifest.read_bytes()

    errors = pin_exact_requirement(
        "9.9.9", pyproject_path=pyproject, manifest_path=manifest
    )

    assert "pyproject version does not match the requested release" in errors
    assert "manifest version does not match the requested release" in errors
    assert any("only uk-bin-collection" in error for error in errors)
    assert manifest.read_bytes() == before


@pytest.mark.parametrize(
    "requirements",
    [
        None,
        "uk-bin-collection>=1.2.3",
        [],
        ["uk-bin-collection>=1.2.3", "other-package==1.0"],
        [123],
    ],
    ids=[
        "missing",
        "not-a-list",
        "empty",
        "multiple-packages",
        "non-string",
    ],
)
def test_pin_refuses_malformed_requirement_shapes(
    tmp_path: Path,
    requirements: object,
) -> None:
    pyproject, manifest = _write_release_files(tmp_path, "uk-bin-collection>=1.2.3")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["requirements"] = requirements
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    before = manifest.read_bytes()

    errors = pin_exact_requirement(
        "1.2.3", pyproject_path=pyproject, manifest_path=manifest
    )

    assert errors == [
        "manifest requirements must contain only uk-bin-collection before pinning"
    ]
    assert manifest.read_bytes() == before


@pytest.mark.parametrize(
    ("argv", "expected_check_only", "expected_action"),
    [
        (["--version", "1.2.3"], False, "pinned"),
        (["--version", "1.2.3", "--check"], True, "can be pinned"),
    ],
)
def test_main_reports_success_without_bypassing_requested_mode(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    expected_check_only: bool,
    expected_action: str,
) -> None:
    calls: list[tuple[str, bool]] = []

    def successful_pin(version: str, *, check_only: bool = False) -> list[str]:
        calls.append((version, check_only))
        return []

    monkeypatch.setattr(pin_release_manifest, "pin_exact_requirement", successful_pin)

    assert pin_release_manifest.main(argv) == 0
    captured = capsys.readouterr()
    assert calls == [("1.2.3", expected_check_only)]
    assert (
        captured.out == f"HA manifest {expected_action} to uk-bin-collection==1.2.3.\n"
    )
    assert captured.err == ""


def test_main_reports_every_validation_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    errors = ["version mismatch", "unexpected requirement"]

    monkeypatch.setattr(
        pin_release_manifest,
        "pin_exact_requirement",
        lambda version, *, check_only=False: errors,
    )

    assert pin_release_manifest.main(["--version", "1.2.3", "--check"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ("ERROR: version mismatch\nERROR: unexpected requirement\n")


def test_module_entrypoint_runs_repository_check_without_mutating_manifest(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_before = pin_release_manifest.MANIFEST.read_bytes()
    version = json.loads(manifest_before)["version"]
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(pin_release_manifest.__file__),
            "--version",
            version,
            "--check",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(pin_release_manifest.__file__), run_name="__main__")

    assert exc_info.value.code == 0
    assert pin_release_manifest.MANIFEST.read_bytes() == manifest_before
    captured = capsys.readouterr()
    assert (
        captured.out == f"HA manifest can be pinned to uk-bin-collection=={version}.\n"
    )
    assert captured.err == ""
