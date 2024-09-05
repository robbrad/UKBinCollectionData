from unittest.mock import MagicMock, patch
import argparse
import pytest
from uk_bin_collection.collect_data import UKBinCollectionApp, import_council_module



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
        "web_driver",
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
@patch("uk_bin_collection.collect_data.setup_logging")  # Correct patch path
@patch("uk_bin_collection.collect_data.UKBinCollectionApp.run")  # Correct patch path
@patch("sys.argv", ["uk_bin_collection.py", "council_module", "http://example.com"])
def test_run_function(mock_app_run, mock_setup_logging):
    from uk_bin_collection.collect_data import run

    mock_setup_logging.return_value = MagicMock()
    mock_app_run.return_value = None

    run()

    # Ensure logging was set up and the app run method was called
    mock_setup_logging.assert_called_once()
    mock_app_run.assert_called_once()
