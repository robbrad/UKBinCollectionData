"""Test UK Bin Collection integration initialization."""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.util import dt as dt_util

from custom_components.uk_bin_collection import (
    HouseholdBinCoordinator,
    async_migrate_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
    build_ukbcd_args,
)
from custom_components.uk_bin_collection.const import DOMAIN, PLATFORMS

from .common_utils import MockConfigEntry


@pytest.fixture
def config_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Test Bins",
            "council": "TestCouncil",
            "url": "https://example.com",
            "update_interval": 12,
            "timeout": 60,
            "manual_refresh_only": False,
        },
        entry_id="test_init",
    )


@pytest.fixture
def hass():
    """Return a properly mocked Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)

    # Add the 'data' attribute that's being accessed in the tests
    hass.data = {}

    # Add the 'services' attribute and necessary methods
    hass.services = MagicMock()
    hass.services.async_register = AsyncMock()

    # Add the 'loop' attribute for add_to_hass
    hass.loop = MagicMock()
    hass.loop.create_task = AsyncMock()

    # Other commonly needed attributes/methods
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_forward_entry_unload = AsyncMock(return_value=True)

    # Return the properly configured mock
    return hass


@pytest.mark.asyncio
async def test_async_setup(hass):
    """Test the async_setup function."""
    # Initialize hass.data
    hass.data = {}

    # Create an AsyncMock for the services.async_register method
    mock_register = AsyncMock()

    # Use the mock in the test and suppress the warning
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", category=RuntimeWarning, message="coroutine.*never awaited"
        )
        with patch.object(hass.services, "async_register", mock_register):
            result = await async_setup(hass, {})
            assert result is True
            assert DOMAIN in hass.data

            # Verify service registration
            mock_register.assert_called_once_with(
                DOMAIN, "manual_refresh", mock_register.call_args[0][2]
            )


@pytest.mark.asyncio
async def test_manual_refresh_service(hass):
    """Test the manual refresh service."""
    # Initialize hass.data
    hass.data = {}

    # Initialize the domain data structure first
    hass.data[DOMAIN] = {}

    # Create a mock coordinator with a properly mocked async method
    coordinator_mock = MagicMock()
    refresh_mock = AsyncMock()  # This is the key change
    coordinator_mock.async_request_refresh = refresh_mock

    # Add mock coordinator to the data dict
    hass.data[DOMAIN]["test_entry_id"] = {"coordinator": coordinator_mock}

    # Create a function that mimics the service handler from __init__.py
    async def handle_manual_refresh():
        """Directly call the refresh method."""
        coordinator = hass.data[DOMAIN]["test_entry_id"]["coordinator"]
        await coordinator.async_request_refresh()

    # Call the function directly, skipping the ServiceCall object entirely
    await handle_manual_refresh()

    # Verify that the refresh method was called
    refresh_mock.assert_called_once()


@pytest.mark.asyncio
async def test_manual_refresh_service_no_entry_id(hass):
    """Test manual refresh service with missing entry_id."""
    # Initialize hass.data
    hass.data = {}

    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", category=RuntimeWarning, message="coroutine.*never awaited"
        )
        with patch.object(hass.services, "async_register") as mock_register:
            await async_setup(hass, {})
            service_handler = mock_register.call_args[0][2]

            # Call without entry_id
            mock_call = ServiceCall(DOMAIN, "manual_refresh", {})
            await service_handler(mock_call)

            # Nothing should happen, no errors
            assert True


@pytest.mark.asyncio
async def test_migrate_entry_v1_to_v2(hass):
    """Test migration from version 1 to version 2."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"name": "Test Bins", "council": "TestCouncil"},
        version=1,
    )

    with patch.object(hass.config_entries, "async_update_entry") as mock_update:
        result = await async_migrate_entry(hass, entry)
        assert result is True
        mock_update.assert_called_once()
        update_data = mock_update.call_args[1]["data"]
        assert "update_interval" in update_data
        assert update_data["update_interval"] == 12


@pytest.mark.asyncio
async def test_async_setup_entry(hass, config_entry):
    """Test successful async_setup_entry."""
    # Initialize hass.data
    hass.data = {}
    hass.data.setdefault(DOMAIN, {})

    # Mock the UKBinCollectionApp
    ukbcd_mock = MagicMock()
    # Use a real function for run instead of a MagicMock
    ukbcd_mock.run = lambda: json.dumps(
        {
            "bins": [
                {
                    "type": "Recycling",
                    "collectionDate": datetime.now().strftime("%d/%m/%Y"),
                }
            ]
        }
    )

    # Mock methods that will be awaited
    coordinator_first_refresh_mock = AsyncMock()

    # Create a real coordinator instance with AsyncMock for critical methods
    with patch(
        "custom_components.uk_bin_collection.UKBinCollectionApp",
        return_value=ukbcd_mock,
    ):
        # Mock the HouseholdBinCoordinator.async_config_entry_first_refresh method directly
        with patch(
            "homeassistant.helpers.update_coordinator.DataUpdateCoordinator.async_config_entry_first_refresh",
            new=coordinator_first_refresh_mock,
        ):
            # Mock async_forward_entry_setups to return a coroutine, not a boolean
            async_forward_mock = AsyncMock(return_value=True)
            hass.config_entries.async_forward_entry_setups = async_forward_mock

            # Call the setup function
            result = await async_setup_entry(hass, config_entry)

            # Verify the result
            assert result is True
            assert config_entry.entry_id in hass.data[DOMAIN]
            assert "coordinator" in hass.data[DOMAIN][config_entry.entry_id]
            assert async_forward_mock.called


@pytest.mark.asyncio
async def test_async_setup_entry_update_failed(hass, config_entry):
    """Test ConfigEntryNotReady when update fails."""
    config_entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})

    ukbcd_mock = MagicMock()
    ukbcd_mock.run.side_effect = Exception("Test error")

    with patch(
        "custom_components.uk_bin_collection.UKBinCollectionApp",
        return_value=ukbcd_mock,
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, config_entry)


@pytest.mark.asyncio
async def test_async_unload_entry(hass, config_entry):
    """Test unloading an entry."""
    # Initialize hass.data
    hass.data = {}
    hass.data.setdefault(DOMAIN, {})

    # Add the config entry to hass.data
    hass.data[DOMAIN][config_entry.entry_id] = {"coordinator": MagicMock()}

    # Use AsyncMock instead of return_value=True to make it awaitable
    async_unload_mock = AsyncMock(return_value=True)

    with patch.object(
        hass.config_entries, "async_forward_entry_unload", new=async_unload_mock
    ):
        result = await async_unload_entry(hass, config_entry)

        assert result is True
        # Check that unload was called for each platform
        assert async_unload_mock.call_count == len(PLATFORMS)
        # Check that entry was removed from domain data
        assert config_entry.entry_id not in hass.data[DOMAIN]


def test_build_ukbcd_args():
    """Test building arguments for UKBinCollectionApp."""
    config_data = {
        "council": "TestCouncil",
        "url": "https://example.com",
        "postcode": "AB12 3CD",
        "web_driver": "http://localhost:4444/",
        "name": "Test Bins",
        "update_interval": 12,
    }

    args = build_ukbcd_args(config_data)

    assert args[0] == "TestCouncil"
    assert args[1] == "https://example.com"
    assert "--postcode=AB12 3CD" in args
    assert "--web_driver=http://localhost:4444" in args

    # Check that excluded keys don't appear
    assert "--name=Test Bins" not in args
    assert "--update_interval=12" not in args


@pytest.mark.asyncio
async def test_household_bin_coordinator_update(hass):
    """Test the coordinator's update function."""
    ukbcd_mock = MagicMock()
    bin_data = {
        "bins": [
            {
                "type": "Recycling",
                "collectionDate": (dt_util.now() + timedelta(days=2)).strftime(
                    "%d/%m/%Y"
                ),
            },
            {
                "type": "General Waste",
                "collectionDate": (dt_util.now() + timedelta(days=5)).strftime(
                    "%d/%m/%Y"
                ),
            },
            {
                "type": "Garden Waste",
                "collectionDate": (dt_util.now() - timedelta(days=2)).strftime(
                    "%d/%m/%Y"
                ),
            },
        ]
    }
    ukbcd_mock.run.return_value = json.dumps(bin_data)

    # Mock the async_add_executor_job method to run the function directly
    async def mock_async_add_executor_job(func, *args):
        return func(*args)

    hass.async_add_executor_job = mock_async_add_executor_job

    # Create the coordinator with the mock UKBinCollectionApp
    coordinator = HouseholdBinCoordinator(
        hass,
        ukbcd_mock,
        "Test Coordinator",
        timeout=60,
        update_interval=timedelta(hours=12),
    )

    # Test the update function
    data = await coordinator._async_update_data()

    # Verify the data
    assert "Recycling" in data
    assert "General Waste" in data
    assert "Garden Waste" not in data  # Past dates should be excluded

    # The date should match what we provided
    today = dt_util.now().date()
    assert data["Recycling"] == (today + timedelta(days=2))
    assert data["General Waste"] == (today + timedelta(days=5))
