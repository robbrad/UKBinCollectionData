#!/usr/bin/env python3
"""Prepare the HA manifest for an atomic, exact-version release tag."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
MANIFEST = ROOT / "custom_components" / "uk_bin_collection" / "manifest.json"
CORE_REQUIREMENT = re.compile(r"^uk-bin-collection(?:\s*[<>=!~].*)?$", re.I)


def validate_pin_inputs(
    version: str,
    *,
    pyproject_path: Path = PYPROJECT,
    manifest_path: Path = MANIFEST,
) -> tuple[dict, list[str]]:
    """Return parsed manifest and fail-closed reasons it cannot be pinned."""
    project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    if project["tool"]["poetry"]["version"] != version:
        errors.append("pyproject version does not match the requested release")
    if manifest.get("version") != version:
        errors.append("manifest version does not match the requested release")

    requirements = manifest.get("requirements")
    if (
        not isinstance(requirements, list)
        or len(requirements) != 1
        or not isinstance(requirements[0], str)
        or not CORE_REQUIREMENT.fullmatch(requirements[0].strip())
    ):
        errors.append(
            "manifest requirements must contain only uk-bin-collection before pinning"
        )
    return manifest, errors


def pin_exact_requirement(
    version: str,
    *,
    pyproject_path: Path = PYPROJECT,
    manifest_path: Path = MANIFEST,
    check_only: bool = False,
) -> list[str]:
    """Pin the matching core package, or only prove the mutation is safe."""
    manifest, errors = validate_pin_inputs(
        version,
        pyproject_path=pyproject_path,
        manifest_path=manifest_path,
    )
    if errors or check_only:
        return errors

    manifest["requirements"] = [f"uk-bin-collection=={version}"]
    manifest_path.write_text(
        json.dumps(manifest, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    errors = pin_exact_requirement(args.version, check_only=args.check)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    action = "can be pinned" if args.check else "pinned"
    print(f"HA manifest {action} to uk-bin-collection=={args.version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
