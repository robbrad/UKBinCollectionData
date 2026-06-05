"""
Pytest configuration for South Kesteven District Council tests.
"""

import os

import pytest


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test that requires external services"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle integration tests."""
    pass


@pytest.fixture
def test_postcode():
    """Provide a test postcode for South Kesteven."""
    return os.environ.get("UKBC_TEST_POSTCODE", "NG31 8XG")


@pytest.fixture
def test_paon():
    """Provide a test property number for South Kesteven."""
    return os.environ.get("UKBC_TEST_PAON", "43")


@pytest.fixture
def test_url():
    """Provide a target URL for South Kesteven local validation."""
    return os.environ.get("UKBC_TEST_URL", "https://www.southkesteven.gov.uk/binday")


@pytest.fixture
def test_web_driver():
    """Provide an optional remote Selenium WebDriver URL."""
    return os.environ.get("UKBC_TEST_WEB_DRIVER") or None


@pytest.fixture
def test_headless():
    """Provide a bool-ish headless setting from the local validation environment."""
    return os.environ.get("UKBC_TEST_HEADLESS", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
