"""Test UK Bin Collection component compatibility."""
import pytest
from unittest.mock import Mock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.uk_bin_collection import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
    build_ukbcd_args,
)
from custom_components.uk_bin_collection.const import DOMAIN


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return Mock(spec=ConfigEntry, data={
        "name": "Test Council",
        "council": "TestCouncil",
        "url": "https://example.com",
        "timeout": 60,
        "manual_refresh_only": False,
        "update_interval": 12,
        "icon_color_mapping": "{}"
    })


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    hass.services = Mock()
    hass.config_entries = Mock()
    return hass


def test_build_ukbcd_args():
    """Test building arguments for UKBinCollectionApp."""
    config_data = {
        "council": "TestCouncil",
        "url": "https://example.com",
        "postcode": "SW1A 1AA",
        "uprn": "123456789",
        "headless": True,
        "web_driver": "http://localhost:4444/wd/hub",
        "timeout": 60,  # Should be excluded
        "name": "Test",  # Should be excluded
    }
    
    args = build_ukbcd_args(config_data)
    
    assert "TestCouncil" in args
    assert "https://example.com" in args
    assert "--postcode=SW1A 1AA" in args
    assert "--uprn=123456789" in args
    assert "--headless" in args
    assert "--web_driver=http://localhost:4444/wd/hub" in args
    
    # These should be excluded
    assert not any("--timeout" in arg for arg in args)
    assert not any("--name" in arg for arg in args)


@pytest.mark.asyncio
async def test_async_setup(mock_hass):
    """Test component setup."""
    config = {}
    
    result = await async_setup(mock_hass, config)
    
    assert result is True
    assert DOMAIN in mock_hass.data
    mock_hass.services.async_register.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_success(mock_hass, mock_config_entry):
    """Test successful config entry setup."""
    mock_config_entry.entry_id = "test_entry"
    
    with patch('custom_components.uk_bin_collection.UKBinCollectionApp') as mock_app, \
         patch('custom_components.uk_bin_collection.HouseholdBinCoordinator') as mock_coordinator:
        
        mock_coordinator_instance = Mock()
        mock_coordinator_instance.async_config_entry_first_refresh = Mock()
        mock_coordinator.return_value = mock_coordinator_instance
        
        result = await async_setup_entry(mock_hass, mock_config_entry)
        
        assert result is True
        assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once()


@pytest.mark.asyncio
async def test_async_unload_entry(mock_hass, mock_config_entry):
    """Test config entry unloading."""
    mock_config_entry.entry_id = "test_entry"
    mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {"coordinator": Mock()}
    
    mock_hass.config_entries.async_forward_entry_unload.return_value = True
    
    result = await async_unload_entry(mock_hass, mock_config_entry)
    
    assert result is True
    assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]


def test_component_imports():
    """Test that all required modules can be imported."""
    try:
        from custom_components.uk_bin_collection import const
        from custom_components.uk_bin_collection import config_flow
        from custom_components.uk_bin_collection import sensor
        from custom_components.uk_bin_collection import calendar
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import component modules: {e}")


def test_manifest_structure():
    """Test manifest.json has required structure."""
    import json
    import os
    
    manifest_path = os.path.join(
        os.path.dirname(__file__), "..", "manifest.json"
    )
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    required_fields = [
        "domain", "name", "version", "requirements", 
        "config_flow", "dependencies", "codeowners"
    ]
    
    for field in required_fields:
        assert field in manifest, f"Missing required field: {field}"
    
    assert manifest["domain"] == "uk_bin_collection"
    assert isinstance(manifest["requirements"], list)
    assert len(manifest["requirements"]) > 0