"""Tests for fail-closed release-manifest pinning."""

from __future__ import annotations

import json
from pathlib import Path

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
