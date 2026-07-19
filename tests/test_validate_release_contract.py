"""Tests for the fail-closed release contract."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import runpy
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "validate_release_contract.py"
)
SPEC = importlib.util.spec_from_file_location("validate_release_contract", SCRIPT)
assert SPEC and SPEC.loader
release_contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_contract)


def _write_project(
    tmp_path: Path,
    *,
    requirement: str,
    project_version: str = "1.2.3",
    manifest_version: str = "1.2.3",
) -> tuple[Path, Path]:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        f'[tool.poetry]\nversion = "{project_version}"\n', encoding="utf-8"
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "version": manifest_version,
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


def test_release_metadata_reports_core_and_component_version_mismatches(
    tmp_path: Path,
) -> None:
    pyproject, manifest = _write_project(
        tmp_path,
        requirement="uk-bin-collection==1.2.3",
        project_version="1.2.2",
        manifest_version="1.2.4",
    )

    assert release_contract.validate_release_metadata(
        "1.2.3",
        require_exact=True,
        pyproject_path=pyproject,
        manifest_path=manifest,
    ) == [
        "pyproject version '1.2.2' does not match '1.2.3'",
        "manifest version '1.2.4' does not match '1.2.3'",
    ]


def test_wheel_metadata_must_match_release_version(tmp_path: Path) -> None:
    wheel = _write_wheel(tmp_path, version="1.2.4")
    errors = release_contract.validate_wheel(wheel, "1.2.3")
    assert any("wheel version" in error for error in errors)


def test_wheel_must_contain_exactly_one_metadata_file(tmp_path: Path) -> None:
    wheel = tmp_path / "missing-metadata.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("uk_bin_collection/__init__.py", "")
    assert release_contract.validate_wheel(wheel, "1.2.3") == [
        "wheel must contain exactly one dist-info/METADATA; found 0"
    ]

    wheel = tmp_path / "duplicate-metadata.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "one.dist-info/METADATA",
            "Name: uk-bin-collection\nVersion: 1.2.3\nRequires-Python: >=3.12\n",
        )
        archive.writestr(
            "two.dist-info/METADATA",
            "Name: uk-bin-collection\nVersion: 1.2.3\nRequires-Python: >=3.12\n",
        )
    assert release_contract.validate_wheel(wheel, "1.2.3") == [
        "wheel must contain exactly one dist-info/METADATA; found 2"
    ]


def test_wheel_must_be_a_readable_zip_archive(tmp_path: Path) -> None:
    wheel = tmp_path / "invalid.whl"
    wheel.write_text("not a zip archive", encoding="utf-8")

    errors = release_contract.validate_wheel(wheel, "1.2.3")

    assert len(errors) == 1
    assert errors[0].startswith(f"cannot read wheel {wheel}:")


def test_wheel_rejects_wrong_distribution_and_missing_python_metadata(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "wrong-package.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "wrong_package-1.2.3.dist-info/METADATA",
            "Metadata-Version: 2.4\n" "Name: wrong_package\n" "Version: 1.2.3\n",
        )

    assert release_contract.validate_wheel(wheel, "1.2.3") == [
        "wheel distribution 'wrong_package' is not 'uk-bin-collection'",
        "wheel is missing Requires-Python metadata",
    ]


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


def test_pypi_release_json_must_be_readable(tmp_path: Path) -> None:
    wheel = _write_wheel(tmp_path)
    release_json = tmp_path / "release.json"
    release_json.write_text("{", encoding="utf-8")

    errors = release_contract.validate_pypi_digest(wheel, release_json, "1.2.3")

    assert len(errors) == 1
    assert errors[0].startswith(f"cannot read PyPI release JSON {release_json}:")


def test_pypi_release_must_match_version_and_contain_the_wheel(
    tmp_path: Path,
) -> None:
    wheel = _write_wheel(tmp_path)
    release_json = tmp_path / "release.json"
    release_json.write_text(
        json.dumps(
            {
                "info": {"version": "1.2.4"},
                "urls": [{"filename": "another-file.whl"}],
            }
        ),
        encoding="utf-8",
    )

    assert release_contract.validate_pypi_digest(wheel, release_json, "1.2.3") == [
        "PyPI JSON version '1.2.4' does not match '1.2.3'",
        f"PyPI JSON must contain exactly one {wheel.name!r}; found 0",
    ]


def test_main_runs_all_requested_validators_and_reports_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    wheel = tmp_path / "candidate.whl"
    release_json = tmp_path / "release.json"
    calls: list[tuple[object, ...]] = []

    def validate_metadata(version: str, *, require_exact: bool) -> list[str]:
        calls.append(("metadata", version, require_exact))
        return []

    def validate_wheel(wheel_path: Path, version: str) -> list[str]:
        calls.append(("wheel", wheel_path, version))
        return []

    def validate_digest(
        wheel_path: Path, pypi_json_path: Path, version: str
    ) -> list[str]:
        calls.append(("pypi", wheel_path, pypi_json_path, version))
        return []

    monkeypatch.setattr(
        release_contract, "validate_release_metadata", validate_metadata
    )
    monkeypatch.setattr(release_contract, "validate_wheel", validate_wheel)
    monkeypatch.setattr(release_contract, "validate_pypi_digest", validate_digest)

    result = release_contract.main(
        [
            "--version",
            "1.2.3",
            "--require-exact",
            "--wheel",
            str(wheel),
            "--pypi-json",
            str(release_json),
        ]
    )

    assert result == 0
    assert calls == [
        ("metadata", "1.2.3", True),
        ("wheel", wheel, "1.2.3"),
        ("pypi", wheel, release_json, "1.2.3"),
    ]
    assert capsys.readouterr().out == (
        "Release contract valid for 1.2.3: core/component versions, "
        "exact HA core requirement, wheel metadata, published wheel SHA-256.\n"
    )


def test_main_reports_all_errors_and_requires_a_wheel_for_pypi_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    release_json = tmp_path / "release.json"
    monkeypatch.setattr(
        release_contract,
        "validate_release_metadata",
        lambda version, *, require_exact: ["metadata mismatch"],
    )

    result = release_contract.main(
        ["--version", "1.2.3", "--pypi-json", str(release_json)]
    )

    assert result == 1
    assert capsys.readouterr().err == (
        "ERROR: metadata mismatch\nERROR: --pypi-json requires --wheel\n"
    )


def test_script_entrypoint_validates_the_repository_release_contract(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = release_contract.tomllib.loads(
        (SCRIPT.parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )
    version = project["tool"]["poetry"]["version"]
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--version", version])

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(SCRIPT), run_name="__main__")

    assert exc_info.value.code == 0
    assert capsys.readouterr().out.startswith(f"Release contract valid for {version}:")
