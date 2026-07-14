"""Validation for optional dependencies that are imported at runtime."""

from __future__ import annotations

import os
from importlib import metadata, util
from pathlib import Path

from uk_bin_collection.uk_bin_collection.exceptions import (
    DependencyShadowingError,
    MissingDependencyError,
)

WEBSOCKET_DISTRIBUTION = "websocket-client"
WEBSOCKET_IMPORT_NAME = "websocket"
_WEBSOCKET_INIT = "websocket/__init__.py"


def _normalised_path(path: os.PathLike[str] | str) -> str:
    """Return a real, case-normalised path suitable for identity comparison."""
    return os.path.normcase(os.path.realpath(os.fspath(path)))


def _owned_websocket_init_files(distribution: metadata.Distribution) -> set[str]:
    """Return websocket package entry points owned by ``websocket-client``."""
    owned_files: set[str] = set()
    for relative_path in distribution.files or ():
        portable_path = str(relative_path).replace("\\", "/")
        if portable_path == _WEBSOCKET_INIT:
            owned_files.add(_normalised_path(distribution.locate_file(relative_path)))
    return owned_files


def validate_websocket_client() -> Path:
    """Verify that ``websocket`` resolves to the ``websocket-client`` package.

    Selenium imports the top-level module named ``websocket``.  Home Assistant's
    configuration directory is importable, so an unrelated ``/config/websocket``
    package can otherwise win normal import resolution.  Comparing the resolved
    module file with the files recorded in installed distribution metadata catches
    that collision without modifying ``sys.path`` or importing the suspect module.

    Returns:
        The verified path to ``websocket/__init__.py``.

    Raises:
        MissingDependencyError: ``websocket-client`` is absent or incomplete.
        DependencyShadowingError: ``websocket`` resolves outside that distribution.
    """
    try:
        distribution = metadata.distribution(WEBSOCKET_DISTRIBUTION)
    except metadata.PackageNotFoundError as exc:
        raise MissingDependencyError(
            "The optional dependency 'websocket-client' is required for Selenium."
        ) from exc

    owned_files = _owned_websocket_init_files(distribution)
    if not owned_files:
        raise MissingDependencyError(
            "The installed 'websocket-client' distribution does not contain "
            "websocket/__init__.py. Reinstall the dependency before using Selenium."
        )

    try:
        specification = util.find_spec(WEBSOCKET_IMPORT_NAME)
    except (AttributeError, ImportError, ValueError) as exc:
        raise DependencyShadowingError(
            "Python cannot safely resolve the 'websocket' module required by "
            "'websocket-client'. Remove or rename the conflicting top-level package."
        ) from exc

    if specification is None or specification.origin is None:
        raise MissingDependencyError(
            "The 'websocket-client' distribution is installed but its 'websocket' "
            "module cannot be resolved."
        )

    resolved_path = _normalised_path(specification.origin)
    if resolved_path not in owned_files:
        expected_parent = Path(next(iter(owned_files))).parent
        raise DependencyShadowingError(
            "The top-level 'websocket' import is shadowed by an unrelated package "
            f"at {specification.origin!s}. It must resolve from {expected_parent!s}."
        )

    if not Path(resolved_path).is_file():
        raise MissingDependencyError(
            "The 'websocket-client' distribution metadata points to a missing "
            "websocket/__init__.py file. Reinstall the dependency."
        )

    return Path(resolved_path)
