import argparse
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from uk_bin_collection.uk_bin_collection import collect_data
from uk_bin_collection.uk_bin_collection.collect_data import (
    UKBinCollectionApp,
)
from uk_bin_collection.uk_bin_collection.exceptions import (
    InvalidCouncilModuleError,
    MissingDependencyError,
)


def _configure_registered_council(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Path:
    """Configure a trusted synthetic council for loader branch tests."""
    council_file = tmp_path / "ExampleCouncil.py"
    council_file.write_text("# synthetic council\n", encoding="utf-8")
    monkeypatch.setattr(
        collect_data,
        "registered_council_modules",
        lambda: frozenset({"ExampleCouncil"}),
    )
    monkeypatch.setattr(
        collect_data, "council_requires_selenium", lambda _module_name: False
    )
    monkeypatch.setattr(
        collect_data, "_council_file", lambda _module_name: council_file
    )
    return council_file


# Test UKBinCollectionApp setup_arg_parser
def test_setup_arg_parser():
    app = UKBinCollectionApp()
    app.setup_arg_parser()

    # Assert that the argument parser has the correct arguments
    assert isinstance(app.parser, argparse.ArgumentParser)
    args = app.parser._actions
    arg_names = [action.dest for action in args]

    expected_args = [
        "module",
        "URL",
        "postcode",
        "number",
        "skip_get_url",
        "uprn",
        "usrn",
        "web_driver",
        "artifact_dir",
        "user_agent",
        "headless",
        "local_browser",
        "dev_mode",
    ]
    assert all(arg in arg_names for arg in expected_args)


# Test UKBinCollectionApp set_args
def test_set_args():
    app = UKBinCollectionApp()
    app.setup_arg_parser()

    # Test valid args
    args = ["council_module", "http://example.com", "--postcode", "AB1 2CD"]
    app.set_args(args)

    assert app.parsed_args.module == "council_module"
    assert app.parsed_args.URL == "http://example.com"
    assert app.parsed_args.postcode == "AB1 2CD"
    assert app.parsed_args.headless is True


# Test UKBinCollectionApp client_code method
def test_client_code():
    app = UKBinCollectionApp()
    mock_get_bin_data_class = MagicMock()

    # Run the client_code and ensure that template_method is called
    app.client_code(mock_get_bin_data_class, "http://example.com", postcode="AB1 2CD")
    mock_get_bin_data_class.template_method.assert_called_once_with(
        "http://example.com", postcode="AB1 2CD"
    )


# Test the run() function with logging setup
@patch("uk_bin_collection.uk_bin_collection.collect_data.setup_logging")
@patch("uk_bin_collection.uk_bin_collection.collect_data.UKBinCollectionApp.run")
@patch("sys.argv", ["uk_bin_collection.py", "council_module", "http://example.com"])
def test_run_function(mock_app_run, mock_setup_logging):
    from uk_bin_collection.uk_bin_collection.collect_data import run

    mock_setup_logging.return_value = MagicMock()
    mock_app_run.return_value = None

    run()

    # Ensure logging was set up and the app run method was called
    mock_setup_logging.assert_called_once()
    mock_app_run.assert_called_once()


def test_run_propagates_all_supported_arguments():
    app = UKBinCollectionApp()
    app.set_args(
        [
            "ExampleCouncil",
            "https://example.invalid/collections",
            "--postcode=AB1 2CD",
            "--number=42A",
            "--uprn=100012345",
            "--usrn=200012345",
            "--skip_get_url",
            "--web_driver=http://selenium.invalid:4444/wd/hub",
            "--artifact_dir=/tmp/ukbcd-artifacts",
            "--user_agent=UKBCD contract test",
            "--not-headless",
            "--local_browser",
            "--dev_mode",
        ]
    )
    council = MagicMock()
    module = MagicMock()
    module.CouncilClass.return_value = council

    with patch(
        "uk_bin_collection.uk_bin_collection.collect_data.import_council_module",
        return_value=module,
    ):
        app.run()

    council.template_method.assert_called_once_with(
        "https://example.invalid/collections",
        postcode="AB1 2CD",
        paon="42A",
        uprn="100012345",
        usrn="200012345",
        skip_get_url=True,
        web_driver="http://selenium.invalid:4444/wd/hub",
        artifact_dir="/tmp/ukbcd-artifacts",
        user_agent="UKBCD contract test",
        headless=False,
        local_browser=True,
        dev_mode=True,
        council_module_str="ExampleCouncil",
    )


def test_council_requires_selenium_detects_direct_import(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    council_file = tmp_path / "DirectImportCouncil.py"
    council_file.write_text("import selenium.webdriver\n", encoding="utf-8")
    monkeypatch.setattr(
        collect_data, "_council_file", lambda _module_name: council_file
    )

    collect_data.council_requires_selenium.cache_clear()
    try:
        assert collect_data.council_requires_selenium("DirectImportCouncil") is True
    finally:
        collect_data.council_requires_selenium.cache_clear()


def test_council_requires_selenium_rejects_uninspectable_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    council_file = tmp_path / "BrokenCouncil.py"
    council_file.write_text("from selenium import\n", encoding="utf-8")
    monkeypatch.setattr(
        collect_data, "_council_file", lambda _module_name: council_file
    )

    collect_data.council_requires_selenium.cache_clear()
    try:
        with pytest.raises(
            InvalidCouncilModuleError, match="cannot be inspected safely"
        ) as error:
            collect_data.council_requires_selenium("BrokenCouncil")
    finally:
        collect_data.council_requires_selenium.cache_clear()

    assert isinstance(error.value.__cause__, SyntaxError)


def test_council_loader_wraps_selenium_resolution_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_registered_council(monkeypatch, tmp_path)
    monkeypatch.setattr(
        collect_data, "council_requires_selenium", lambda _module_name: True
    )
    resolution_error = ValueError("selenium.__spec__ is invalid")
    find_spec = MagicMock(side_effect=resolution_error)
    import_module = MagicMock()
    monkeypatch.setattr(collect_data.import_util, "find_spec", find_spec)
    monkeypatch.setattr(collect_data.importlib, "import_module", import_module)

    with pytest.raises(MissingDependencyError, match="cannot safely resolve") as error:
        collect_data.import_council_module("ExampleCouncil")

    assert error.value.__cause__ is resolution_error
    find_spec.assert_called_once_with("selenium")
    import_module.assert_not_called()


def test_council_loader_wraps_qualified_module_resolution_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_registered_council(monkeypatch, tmp_path)
    resolution_error = ImportError("qualified module cannot be resolved")
    find_spec = MagicMock(side_effect=resolution_error)
    import_module = MagicMock()
    monkeypatch.setattr(collect_data.import_util, "find_spec", find_spec)
    monkeypatch.setattr(collect_data.importlib, "import_module", import_module)

    with pytest.raises(
        InvalidCouncilModuleError, match="cannot be resolved safely"
    ) as error:
        collect_data.import_council_module("ExampleCouncil")

    assert error.value.__cause__ is resolution_error
    find_spec.assert_called_once_with(
        "uk_bin_collection.uk_bin_collection.councils.ExampleCouncil"
    )
    import_module.assert_not_called()


def test_council_loader_rejects_module_loaded_from_unexpected_location(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    council_file = _configure_registered_council(monkeypatch, tmp_path)
    specification = SimpleNamespace(origin=str(council_file))
    loaded_module = SimpleNamespace(
        __file__=str(tmp_path / "shadow" / "ExampleCouncil.py"),
        CouncilClass=object,
    )
    monkeypatch.setattr(
        collect_data.import_util, "find_spec", lambda _qualified_name: specification
    )
    monkeypatch.setattr(
        collect_data.importlib, "import_module", lambda _qualified_name: loaded_module
    )

    with pytest.raises(
        InvalidCouncilModuleError, match="loaded from an unexpected location"
    ):
        collect_data.import_council_module("ExampleCouncil")


def test_council_loader_requires_council_class(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    council_file = _configure_registered_council(monkeypatch, tmp_path)
    specification = SimpleNamespace(origin=str(council_file))
    loaded_module = SimpleNamespace(__file__=str(council_file))
    monkeypatch.setattr(
        collect_data.import_util, "find_spec", lambda _qualified_name: specification
    )
    monkeypatch.setattr(
        collect_data.importlib, "import_module", lambda _qualified_name: loaded_module
    )

    with pytest.raises(InvalidCouncilModuleError, match="does not expose CouncilClass"):
        collect_data.import_council_module("ExampleCouncil")
