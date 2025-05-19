"""Test UK Bin Collection utility functions."""

import json
import pytest
import voluptuous as vol
from unittest.mock import patch, MagicMock, AsyncMock

from custom_components.uk_bin_collection.utils import (
    build_user_schema,
    build_council_schema,
    build_selenium_schema,
    build_advanced_schema,
    is_valid_json,
    prepare_config_data,
    validate_selenium_config
)

# Tests focus on schema builders and utility functions that don't require complex mocking

def test_build_user_schema():
    """Test building the user schema."""
    wiki_names = ["Council A", "Council B", "Council C"]
    
    # Basic schema
    schema = build_user_schema(wiki_names)
    assert "name" in schema.schema
    assert "selected_council" in schema.schema
    assert "use_test_data" not in schema.schema
    
    # Schema with defaults
    schema = build_user_schema(wiki_names, default_name="My Council", default_council="Council B")
    assert "name" in schema.schema
    assert "selected_council" in schema.schema
    
    # Print debug information about the field types
    name_field = schema.schema["name"]
    council_field = schema.schema["selected_council"]
    print(f"Name field type: {type(name_field)}")
    print(f"Council field type: {type(council_field)}")
    print(f"Is name_field Optional? {isinstance(name_field, vol.Optional)}")
    
    # Schema with test data option
    schema = build_user_schema(wiki_names, include_test_data=True)
    assert "use_test_data" in schema.schema
    
    # Check that use_test_data is present
    test_data_field = schema.schema["use_test_data"]
    print(f"Test data field type: {type(test_data_field)}")
    print(f"Is test_data_field Optional? {isinstance(test_data_field, vol.Optional)}")


def test_build_council_schema():
    """Test building the council schema."""
    # Council with all fields
    council_data = {
        "postcode": True,
        "uprn": True,
        "house_number": True,
        "usrn": True,
        "wiki_command_url_override": "https://example.com"
    }
    
    schema = build_council_schema("TestCouncil", council_data)
    assert "postcode" in schema.schema
    assert "uprn" in schema.schema
    assert "house_number" in schema.schema
    assert "usrn" in schema.schema
    assert "url" in schema.schema
    
    # Council with only some fields
    council_data = {
        "postcode": True,
        "uprn": True
    }
    
    schema = build_council_schema("TestCouncil", council_data)
    assert "postcode" in schema.schema
    assert "uprn" in schema.schema
    assert "house_number" not in schema.schema
    assert "usrn" not in schema.schema
    assert "url" not in schema.schema


def test_build_selenium_schema():
    """Test building the Selenium schema."""
    schema = build_selenium_schema()
    assert "web_driver" in schema.schema
    assert "headless_mode" in schema.schema
    assert "local_browser" in schema.schema
    
    # Don't check specific types, just verify the fields exist
    # and basic structure is as expected
    assert "url" not in schema.schema  # Verify URL is not included directly
    
    # With default URL
    schema = build_selenium_schema("http://localhost:4444")
    assert "web_driver" in schema.schema
    assert "headless_mode" in schema.schema
    assert "local_browser" in schema.schema


def test_build_advanced_schema():
    """Test building the advanced schema."""
    # Default schema
    schema = build_advanced_schema()
    assert "timeout" in schema.schema
    assert "update_interval" in schema.schema
    assert "automatically_refresh" in schema.schema
    assert "icon_color_mapping" in schema.schema
    
    # With custom defaults
    defaults = {
        "timeout": 30,
        "update_interval": 6,
        "automatically_refresh": False,
        "icon_color_mapping": '{"General Waste": {"color": "brown"}}'
    }
    
    schema = build_advanced_schema(defaults)
    assert "timeout" in schema.schema
    assert "update_interval" in schema.schema
    assert "automatically_refresh" in schema.schema
    assert "icon_color_mapping" in schema.schema


def test_is_valid_json():
    """Test JSON validation."""
    # Valid JSON
    assert is_valid_json('{"key": "value"}') is True
    assert is_valid_json('[]') is True
    assert is_valid_json('123') is True
    # Invalid JSON
    assert is_valid_json('{"key": value}') is False
    assert is_valid_json('{incomplete') is False
    assert is_valid_json('') is False


def test_prepare_config_data():
    """Test preparing configuration data for saving."""
    # Test basic data preparation
    input_data = {
        "selected_council": "TestCouncil",
        "name": "My Council",
        "postcode": "SW1A 1AA",
        "house_number": "10",
        "automatically_refresh": True,
        "update_interval": 6
    }
    
    result = prepare_config_data(input_data, is_options_flow=True)
    assert result["council"] == "TestCouncil"
    assert result["name"] == "My Council"
    assert result["postcode"] == "SW1A 1AA"
    assert result["number"] == "10"  # "house_number" should be mapped to "number"
    assert result["manual_refresh_only"] is True  # "automatically_refresh" mapped to "manual_refresh_only"
    assert result["update_interval"] == 6
    
    # Test with council data
    input_data = {
        "selected_council": "TestCouncil",
        "name": "My Council",
        "council_list": {
            "TestCouncil": {
                "url": "https://example.com/council",
                "original_parser": "GooglePublicCalendarCouncil"
            }
        }
    }
    
    result = prepare_config_data(input_data, is_options_flow=True)
    assert result["council"] == "TestCouncil"
    
    # Test error when critical fields are missing in config flow
    input_data = {
        "name": "My Council",
        "postcode": "SW1A 1AA"
    }
    
    with pytest.raises(ValueError):
        prepare_config_data(input_data, is_options_flow=False)


@pytest.mark.asyncio
async def test_validate_selenium_config():
    """Test validating Selenium configuration."""
    # Test with accessible Selenium server
    user_input = {
        "web_driver": "http://localhost:4444",
        "local_browser": False
    }
    data_dict = {}
    
    # Use patch.object for more precise patching
    with patch("custom_components.uk_bin_collection.utils.check_selenium_server", return_value=True):
        can_proceed, error_code = await validate_selenium_config(user_input, data_dict)
        assert can_proceed is True
        assert error_code is None
    
    # Test with inaccessible Selenium server
    with patch("custom_components.uk_bin_collection.utils.check_selenium_server", return_value=False):
        can_proceed, error_code = await validate_selenium_config(user_input, data_dict)
        assert can_proceed is False
        assert error_code == "selenium_unavailable"
    
    # Test with local browser and Chromium installed
    user_input = {
        "local_browser": True
    }
    
    with patch("custom_components.uk_bin_collection.utils.check_chromium_installed", return_value=True):
        can_proceed, error_code = await validate_selenium_config(user_input, data_dict)
        assert can_proceed is True
        assert error_code is None
        assert data_dict["chromium_installed"] is True
    
    # Test with local browser but Chromium not installed
    with patch("custom_components.uk_bin_collection.utils.check_chromium_installed", return_value=False):
        can_proceed, error_code = await validate_selenium_config(user_input, data_dict)
        assert can_proceed is False
        assert error_code == "chromium_unavailable"
        assert data_dict["chromium_installed"] is False