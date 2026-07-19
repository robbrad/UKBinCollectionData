"""Fail an offline candidate build if its installed dependency graph is incomplete."""

from __future__ import annotations

import argparse
from collections import deque
from importlib import metadata

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def dependency_errors(distribution_name: str) -> list[str]:
    """Return missing or incompatible requirements reachable from a distribution."""
    pending = deque([distribution_name])
    visited: set[str] = set()
    errors: list[str] = []

    while pending:
        requested_name = pending.popleft()
        canonical_name = canonicalize_name(requested_name)
        if canonical_name in visited:
            continue
        visited.add(canonical_name)

        try:
            distribution = metadata.distribution(requested_name)
        except metadata.PackageNotFoundError:
            errors.append(f"missing distribution: {canonical_name}")
            continue

        for raw_requirement in distribution.requires or ():
            requirement = Requirement(raw_requirement)
            if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
                continue

            required_name = canonicalize_name(requirement.name)
            try:
                installed_version = metadata.version(requirement.name)
            except metadata.PackageNotFoundError:
                errors.append(f"missing dependency: {required_name}")
                continue

            if requirement.specifier and not requirement.specifier.contains(
                installed_version, prereleases=True
            ):
                errors.append(
                    f"incompatible dependency: {required_name}=={installed_version}"
                )
                continue
            pending.append(requirement.name)

    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--distribution", required=True)
    args = parser.parse_args()

    errors = dependency_errors(args.distribution)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Installed dependency closure is complete for {args.distribution}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
