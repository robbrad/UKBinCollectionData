import pytest

# Test the command-line options

def test_headless_mode(pytestconfig):
    # Simulate pytest command-line option
    headless_mode_value = pytestconfig.getoption("--headless")
    assert headless_mode_value == "True"  # This should match the default value

def test_local_browser(pytestconfig):
    local_browser_value = pytestconfig.getoption("--local_browser")
    assert local_browser_value == "False"  # This should match the default value

def test_selenium_url(pytestconfig):
    selenium_url_value = pytestconfig.getoption("--selenium_url")
    assert selenium_url_value == "http://localhost:4444"  # This should match the default value

# Test the fixtures

def test_headless_mode_fixture(headless_mode):
    assert headless_mode == "True"  # This should match the default value

def test_local_browser_fixture(local_browser):
    assert local_browser == "False"  # This should match the default value

def test_selenium_url_fixture(selenium_url):
    assert selenium_url == "http://localhost:4444"  # This should match the default value
