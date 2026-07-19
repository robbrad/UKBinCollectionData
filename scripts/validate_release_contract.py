#!/usr/bin/env python3
"""Fail closed unless the HA component and core artifact are version-atomic."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
MANIFEST = ROOT / "custom_components" / "uk_bin_collection" / "manifest.json"
EXPECTED_DISTRIBUTION = "uk-bin-collection"


def _normalise_distribution_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def validate_release_metadata(
    version: str,
    *,
    require_exact: bool,
    pyproject_path: Path = PYPROJECT,
    manifest_path: Path = MANIFEST,
) -> list[str]:
    """Return release-contract errors without mutating any release metadata."""
    project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    errors: list[str] = []
    core_version = project["tool"]["poetry"]["version"]
    component_version = manifest.get("version")
    expected_requirement = f"{EXPECTED_DISTRIBUTION}=={version}"
    requirements = manifest.get("requirements", [])

    if core_version != version:
        errors.append(f"pyproject version {core_version!r} does not match {version!r}")
    if component_version != version:
        errors.append(
            f"manifest version {component_version!r} does not match {version!r}"
        )
    if require_exact and requirements != [expected_requirement]:
        errors.append(
            "manifest must contain only the exact matching core requirement "
            f"{expected_requirement!r}; found {requirements!r}"
        )
    return errors


def validate_wheel(wheel_path: Path, version: str) -> list[str]:
    """Validate identity and version from the wheel's own METADATA."""
    errors: list[str] = []
    try:
        with zipfile.ZipFile(wheel_path) as wheel:
            metadata_files = [
                name
                for name in wheel.namelist()
                if name.endswith(".dist-info/METADATA")
            ]
            if len(metadata_files) != 1:
                return [
                    f"wheel must contain exactly one dist-info/METADATA; "
                    f"found {len(metadata_files)}"
                ]
            metadata = BytesParser().parsebytes(wheel.read(metadata_files[0]))
    except (OSError, zipfile.BadZipFile) as exc:
        return [f"cannot read wheel {wheel_path}: {exc}"]

    distribution_name = metadata.get("Name", "")
    if _normalise_distribution_name(distribution_name) != EXPECTED_DISTRIBUTION:
        errors.append(
            f"wheel distribution {distribution_name!r} is not {EXPECTED_DISTRIBUTION!r}"
        )
    if metadata.get("Version") != version:
        errors.append(
            f"wheel version {metadata.get('Version')!r} does not match {version!r}"
        )
    if not metadata.get("Requires-Python"):
        errors.append("wheel is missing Requires-Python metadata")
    return errors


def validate_pypi_digest(
    wheel_path: Path, pypi_json_path: Path, version: str
) -> list[str]:
    """Prove PyPI serves the exact locally built wheel bytes."""
    try:
        release = json.loads(pypi_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read PyPI release JSON {pypi_json_path}: {exc}"]

    errors: list[str] = []
    if release.get("info", {}).get("version") != version:
        errors.append(
            "PyPI JSON version "
            f"{release.get('info', {}).get('version')!r} does not match {version!r}"
        )

    matching_files = [
        item
        for item in release.get("urls", [])
        if item.get("filename") == wheel_path.name
    ]
    if len(matching_files) != 1:
        errors.append(
            f"PyPI JSON must contain exactly one {wheel_path.name!r}; "
            f"found {len(matching_files)}"
        )
        return errors

    local_digest = hashlib.sha256(wheel_path.read_bytes()).hexdigest()
    remote_digest = matching_files[0].get("digests", {}).get("sha256")
    if remote_digest != local_digest:
        errors.append(
            f"PyPI wheel digest {remote_digest!r} does not match local {local_digest!r}"
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--require-exact", action="store_true")
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--pypi-json", type=Path)
    args = parser.parse_args(argv)

    errors = validate_release_metadata(args.version, require_exact=args.require_exact)
    if args.wheel:
        errors.extend(validate_wheel(args.wheel, args.version))
    if args.pypi_json:
        if not args.wheel:
            errors.append("--pypi-json requires --wheel")
        else:
            errors.extend(
                validate_pypi_digest(args.wheel, args.pypi_json, args.version)
            )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    checks = ["core/component versions"]
    if args.require_exact:
        checks.append("exact HA core requirement")
    if args.wheel:
        checks.append("wheel metadata")
    if args.pypi_json:
        checks.append("published wheel SHA-256")
    print(f"Release contract valid for {args.version}: {', '.join(checks)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
