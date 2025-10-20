"""
Pytest configuration for South Kesteven District Council tests.
"""

import pytest


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test that requires external services"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle integration tests."""
    # Integration tests no longer require Selenium for South Kesteven
    # They use requests-based form submission instead
    pass


@pytest.fixture
def test_postcode():
    """Provide a test postcode for South Kesteven."""
    return "PE6 8BL"


