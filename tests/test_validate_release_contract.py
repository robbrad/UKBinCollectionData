"""Tests for the fail-closed release contract."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "validate_release_contract.py"
)
SPEC = importlib.util.spec_from_file_location("validate_release_contract", SCRIPT)
assert SPEC and SPEC.loader
release_contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_contract)


def _write_project(tmp_path: Path, *, requirement: str) -> tuple[Path, Path]:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.poetry]\nversion = "1.2.3"\n', encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "version": "1.2.3",
                "requirements": [requirement],
            }
        ),
        encoding="utf-8",
    )
    return pyproject, manifest


def _write_wheel(tmp_path: Path, *, version: str = "1.2.3") -> Path:
    wheel = tmp_path / f"uk_bin_collection-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"uk_bin_collection-{version}.dist-info/METADATA",
            "Metadata-Version: 2.4\n"
            "Name: uk-bin-collection\n"
            f"Version: {version}\n"
            "Requires-Python: >=3.12,<3.15\n",
        )
    return wheel


def test_broad_requirement_is_allowed_before_release_but_not_at_release(
    tmp_path: Path,
) -> None:
    pyproject, manifest = _write_project(
        tmp_path, requirement="uk-bin-collection>=1.2.3"
    )
    assert (
        release_contract.validate_release_metadata(
            "1.2.3",
            require_exact=False,
            pyproject_path=pyproject,
            manifest_path=manifest,
        )
        == []
    )
    assert (
        "manifest must contain only"
        in release_contract.validate_release_metadata(
            "1.2.3",
            require_exact=True,
            pyproject_path=pyproject,
            manifest_path=manifest,
        )[0]
    )


def test_wheel_metadata_must_match_release_version(tmp_path: Path) -> None:
    wheel = _write_wheel(tmp_path, version="1.2.4")
    errors = release_contract.validate_wheel(wheel, "1.2.3")
    assert any("wheel version" in error for error in errors)


def test_pypi_digest_must_match_local_wheel(tmp_path: Path) -> None:
    wheel = _write_wheel(tmp_path)
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    release_json = tmp_path / "release.json"
    release_json.write_text(
        json.dumps(
            {
                "info": {"version": "1.2.3"},
                "urls": [
                    {
                        "filename": wheel.name,
                        "digests": {"sha256": digest},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert release_contract.validate_pypi_digest(wheel, release_json, "1.2.3") == []

    payload = json.loads(release_json.read_text(encoding="utf-8"))
    payload["urls"][0]["digests"]["sha256"] = "0" * 64
    release_json.write_text(json.dumps(payload), encoding="utf-8")
    assert (
        "does not match"
        in release_contract.validate_pypi_digest(wheel, release_json, "1.2.3")[0]
    )
