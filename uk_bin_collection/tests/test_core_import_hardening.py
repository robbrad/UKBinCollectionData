"""Focused regression tests for council and Selenium import boundaries."""

from __future__ import annotations

import ast
import builtins
import importlib
import sys
from pathlib import Path, PurePosixPath
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection import common, dependency_validation
from uk_bin_collection.uk_bin_collection import collect_data
from uk_bin_collection.uk_bin_collection.exceptions import (
    DependencyShadowingError,
    InvalidCouncilModuleError,
    MissingDependencyError,
)


class _FakeDistribution:
    def __init__(self, root: Path, *, include_websocket: bool = True) -> None:
        self.root = root
        self.files = (
            [PurePosixPath("websocket/__init__.py")] if include_websocket else []
        )

    def locate_file(self, relative_path: PurePosixPath) -> Path:
        return self.root.joinpath(*relative_path.parts)


def test_websocket_client_accepts_file_owned_by_distribution(tmp_path: Path) -> None:
    expected = tmp_path / "site-packages" / "websocket" / "__init__.py"
    expected.parent.mkdir(parents=True)
    expected.touch()
    distribution = _FakeDistribution(tmp_path / "site-packages")

    with (
        patch.object(
            dependency_validation.metadata,
            "distribution",
            return_value=distribution,
        ),
        patch.object(
            dependency_validation.util,
            "find_spec",
            return_value=SimpleNamespace(origin=str(expected)),
        ),
    ):
        result = dependency_validation.validate_websocket_client()

    assert result == expected.resolve()


def test_websocket_client_reports_stale_distribution_metadata(
    tmp_path: Path,
) -> None:
    expected = tmp_path / "site-packages" / "websocket" / "__init__.py"
    distribution = _FakeDistribution(tmp_path / "site-packages")

    with (
        patch.object(
            dependency_validation.metadata,
            "distribution",
            return_value=distribution,
        ),
        patch.object(
            dependency_validation.util,
            "find_spec",
            return_value=SimpleNamespace(origin=str(expected)),
        ),
        pytest.raises(MissingDependencyError, match="missing"),
    ):
        dependency_validation.validate_websocket_client()


def test_websocket_client_rejects_shadow_package(tmp_path: Path) -> None:
    distribution = _FakeDistribution(tmp_path / "site-packages")
    shadow = tmp_path / "config" / "websocket" / "__init__.py"

    with (
        patch.object(
            dependency_validation.metadata,
            "distribution",
            return_value=distribution,
        ),
        patch.object(
            dependency_validation.util,
            "find_spec",
            return_value=SimpleNamespace(origin=str(shadow)),
        ),
        pytest.raises(DependencyShadowingError, match="shadowed"),
    ):
        dependency_validation.validate_websocket_client()


def test_websocket_client_reports_missing_distribution() -> None:
    with (
        patch.object(
            dependency_validation.metadata,
            "distribution",
            side_effect=dependency_validation.metadata.PackageNotFoundError,
        ),
        pytest.raises(MissingDependencyError, match="websocket-client"),
    ):
        dependency_validation.validate_websocket_client()


def test_websocket_client_rejects_broken_loaded_module_metadata(
    tmp_path: Path,
) -> None:
    distribution = _FakeDistribution(tmp_path / "site-packages")
    with (
        patch.object(
            dependency_validation.metadata,
            "distribution",
            return_value=distribution,
        ),
        patch.object(
            dependency_validation.util,
            "find_spec",
            side_effect=ValueError("websocket.__spec__ is None"),
        ),
        pytest.raises(DependencyShadowingError, match="cannot safely resolve"),
    ):
        dependency_validation.validate_websocket_client()


def test_selenium_is_loaded_only_when_browser_is_requested() -> None:
    with (
        patch.object(common, "find_spec", return_value=None),
        pytest.raises(MissingDependencyError, match="selenium"),
    ):
        common._load_selenium_dependencies()


def test_browser_session_is_closed_when_initialisation_fails() -> None:
    webdriver = MagicMock()
    options = MagicMock()
    webdriver.ChromeOptions.return_value = options
    driver = MagicMock()
    webdriver.Remote.return_value = driver

    class FakeWebDriverError(Exception):
        pass

    driver.set_window_position.side_effect = FakeWebDriverError("window unavailable")
    with (
        patch.object(
            common,
            "_load_selenium_dependencies",
            return_value=(webdriver, FakeWebDriverError),
        ),
        pytest.raises(common.BrowserUnavailableError),
    ):
        common.create_webdriver("http://selenium:4444")

    driver.quit.assert_called_once_with()


@pytest.mark.parametrize(
    "module_name",
    ["", "../SouthKestevenDistrictCouncil", "os.path", "name-with-dash", 123],
)
def test_council_loader_rejects_non_identifier_names(module_name: object) -> None:
    with pytest.raises(InvalidCouncilModuleError):
        collect_data.import_council_module(module_name)  # type: ignore[arg-type]


def test_council_loader_rejects_custom_source_path() -> None:
    with pytest.raises(InvalidCouncilModuleError, match="Custom"):
        collect_data.import_council_module("SouthKestevenDistrictCouncil", "../tmp")


def test_council_loader_imports_only_from_councils_package() -> None:
    expected_file = collect_data._council_file("ExampleCouncil")
    council_module = SimpleNamespace(
        CouncilClass=MagicMock(), __file__=str(expected_file)
    )
    with (
        patch.object(
            collect_data,
            "registered_council_modules",
            return_value=frozenset({"ExampleCouncil"}),
        ),
        patch.object(collect_data, "council_requires_selenium", return_value=False),
        patch.object(
            collect_data.import_util,
            "find_spec",
            return_value=SimpleNamespace(origin=str(expected_file)),
        ),
        patch.object(
            collect_data.importlib,
            "import_module",
            return_value=council_module,
        ) as import_module,
    ):
        result = collect_data.import_council_module("ExampleCouncil")

    assert result is council_module
    import_module.assert_called_once_with(
        "uk_bin_collection.uk_bin_collection.councils.ExampleCouncil"
    )


def test_council_loader_rejects_shadowed_qualified_module(tmp_path: Path) -> None:
    shadow = tmp_path / "config" / "ExampleCouncil.py"
    with (
        patch.object(
            collect_data,
            "registered_council_modules",
            return_value=frozenset({"ExampleCouncil"}),
        ),
        patch.object(collect_data, "council_requires_selenium", return_value=False),
        patch.object(
            collect_data.import_util,
            "find_spec",
            return_value=SimpleNamespace(origin=str(shadow)),
        ),
        patch.object(collect_data.importlib, "import_module") as import_module,
        pytest.raises(InvalidCouncilModuleError, match="outside"),
    ):
        collect_data.import_council_module("ExampleCouncil")

    import_module.assert_not_called()


def test_selenium_council_validates_websocket_before_module_import() -> None:
    with (
        patch.object(
            collect_data,
            "registered_council_modules",
            return_value=frozenset({"ExampleCouncil"}),
        ),
        patch.object(collect_data, "council_requires_selenium", return_value=True),
        patch.object(
            collect_data,
            "validate_websocket_client",
            side_effect=DependencyShadowingError("shadowed"),
        ) as validate,
        patch.object(collect_data.import_util, "find_spec") as find_spec,
        patch.object(collect_data.importlib, "import_module") as import_module,
        pytest.raises(DependencyShadowingError, match="shadowed"),
    ):
        collect_data.import_council_module("ExampleCouncil")

    validate.assert_called_once_with()
    find_spec.assert_called_once_with("selenium")
    import_module.assert_not_called()


def test_selenium_council_reports_missing_optional_dependency_before_import() -> None:
    with (
        patch.object(
            collect_data,
            "registered_council_modules",
            return_value=frozenset({"ExampleCouncil"}),
        ),
        patch.object(collect_data, "council_requires_selenium", return_value=True),
        patch.object(collect_data.import_util, "find_spec", return_value=None),
        patch.object(collect_data, "validate_websocket_client") as validate,
        patch.object(collect_data.importlib, "import_module") as import_module,
        pytest.raises(MissingDependencyError, match="selenium"),
    ):
        collect_data.import_council_module("ExampleCouncil")

    validate.assert_not_called()
    import_module.assert_not_called()


def test_selenium_preflight_detects_eager_and_lazy_imports(
    tmp_path: Path,
) -> None:
    eager_source = tmp_path / "EagerCouncil.py"
    eager_source.write_text("from selenium import webdriver\n", encoding="utf-8")
    lazy_source = tmp_path / "LazyCouncil.py"
    lazy_source.write_text(
        "def load_browser():\n    from selenium import webdriver\n",
        encoding="utf-8",
    )

    collect_data.council_requires_selenium.cache_clear()
    with patch.object(collect_data, "_council_file", return_value=eager_source):
        assert collect_data.council_requires_selenium("EagerCouncil") is True

    collect_data.council_requires_selenium.cache_clear()
    with patch.object(collect_data, "_council_file", return_value=lazy_source):
        assert collect_data.council_requires_selenium("LazyCouncil") is True

    collect_data.council_requires_selenium.cache_clear()


def test_isle_of_wight_lazy_selenium_import_is_preflighted() -> None:
    """A real lazy-import council cannot bypass dependency ownership checks."""
    collect_data.council_requires_selenium.cache_clear()
    assert collect_data.council_requires_selenium("IsleOfWightCouncil") is True
    collect_data.council_requires_selenium.cache_clear()


def test_council_loader_rejects_identifier_not_in_registry() -> None:
    with (
        patch.object(
            collect_data,
            "registered_council_modules",
            return_value=frozenset({"KnownCouncil"}),
        ),
        pytest.raises(InvalidCouncilModuleError, match="installed registry"),
    ):
        collect_data.import_council_module("UnknownCouncil")


def test_non_selenium_council_imports_with_shadow_websocket(monkeypatch) -> None:
    """An unrelated websocket package must not break an HTTP-only council import."""
    fake_websocket = ModuleType("websocket")
    fake_websocket.__file__ = "/config/websocket/__init__.py"
    monkeypatch.setitem(sys.modules, "websocket", fake_websocket)

    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "selenium" or name.startswith("selenium."):
            raise AssertionError("HTTP-only council unexpectedly imported Selenium")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    importlib.reload(common)
    sys.modules.pop(
        "uk_bin_collection.uk_bin_collection.councils.AberdeenCityCouncil", None
    )
    original_import_path = list(sys.path)

    module = collect_data.import_council_module("AberdeenCityCouncil")

    assert module.CouncilClass.__name__ == "CouncilClass"
    assert sys.path == original_import_path


def test_all_council_selenium_imports_are_lazy_and_prevalidated() -> None:
    council_root = (
        Path(__file__).resolve().parents[1] / "uk_bin_collection" / "councils"
    )

    for path in sorted(council_root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        selenium_imports = [
            node
            for node in ast.walk(tree)
            if (
                isinstance(node, ast.Import)
                and any(
                    alias.name == "selenium" or alias.name.startswith("selenium.")
                    for alias in node.names
                )
            )
            or (
                isinstance(node, ast.ImportFrom)
                and node.module
                and (node.module == "selenium" or node.module.startswith("selenium."))
            )
        ]
        if not selenium_imports:
            continue

        assert not any(node in tree.body for node in selenium_imports), path.name
        council_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "CouncilClass"
        )
        parse_data = next(
            node
            for node in council_class.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "parse_data"
        )
        parse_imports = {
            node for node in ast.walk(parse_data) if node in selenium_imports
        }
        if parse_imports != set(selenium_imports):
            support_loader = next(
                (
                    node
                    for node in council_class.body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == "_load_selenium_support"
                ),
                None,
            )
            assert support_loader is not None, path.name
            assert {
                node for node in ast.walk(support_loader) if node in selenium_imports
            } == set(selenium_imports), path.name
            validation_calls = [
                node
                for node in ast.walk(support_loader)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "validate_websocket_client"
            ]
            assert len(validation_calls) == 1, path.name
            assert validation_calls[0].lineno < min(
                node.lineno for node in selenium_imports
            ), path.name
            loader_calls = [
                node
                for node in ast.walk(parse_data)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_load_selenium_support"
            ]
            assert len(loader_calls) == 1, path.name
            continue

        validation_calls = [
            node
            for node in ast.walk(parse_data)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "ensure_selenium_dependencies"
        ]
        assert len(validation_calls) == 1, path.name
        assert validation_calls[0].lineno < min(
            node.lineno for node in selenium_imports
        ), path.name


def test_browser_only_optional_dependencies_are_not_imported_at_module_scope() -> None:
    council_root = (
        Path(__file__).resolve().parents[1] / "uk_bin_collection" / "councils"
    )
    browser_packages = {"selenium", "undetected_chromedriver", "webdriver_manager"}

    for path in sorted(council_root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported = {
                    alias.name.split(".", maxsplit=1)[0] for alias in node.names
                }
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = {node.module.split(".", maxsplit=1)[0]}
            else:
                continue
            assert imported.isdisjoint(browser_packages), path.name
