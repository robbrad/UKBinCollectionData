# test_init.py
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed

# Import the functions and classes from your __init__.py file.
from custom_components.uk_bin_collection import (
    HouseholdBinCoordinator,
    async_migrate_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
    build_ukbcd_args,
)
from custom_components.uk_bin_collection.const import DOMAIN, LOG_PREFIX, PLATFORMS
from uk_bin_collection.uk_bin_collection.collect_data import UKBinCollectionApp


class DummyUKBinCollectionApp:
    def __init__(self):
        self.args = None
        # Set parsed_args so that self.parsed_args.module is valid (using "json" here as an example)
        self.parsed_args = type("DummyArgs", (), {"module": "json"})()

    def set_args(self, args):
        self.args = args
        self.parsed_args = type("DummyArgs", (), {"module": "json"})()

    def run(self):
        # Return valid JSON data expected by the coordinator.
        return json.dumps(
            {
                "bins": [
                    {
                        "type": "waste",
                        "collectionDate": datetime.now().strftime("%d/%m/%Y"),
                    },
                    {
                        "type": "recycling",
                        "collectionDate": (datetime.now() + timedelta(days=1)).strftime(
                            "%d/%m/%Y"
                        ),
                    },
                ]
            }
        )


# Create a dummy config entry for testing.
class DummyConfigEntry:
    def __init__(self, data, version=1, entry_id="dummy_entry"):
        self.data = data
        self.version = version
        self.entry_id = entry_id


# Create a dummy HomeAssistant object.
class DummyHass:
    def __init__(self):
        self.data = {}
        self.services = Services()
        self.config_entries = ConfigEntries()

    async def async_add_executor_job(self, func, *args, **kwargs):
        # In tests, we can simply run the function synchronously.
        return func(*args, **kwargs)


class Services:
    def __init__(self):
        self.registrations = {}

    def async_register(self, domain, service, service_func):
        self.registrations[(domain, service)] = service_func


class ConfigEntries:
    async def async_forward_entry_setups(self, config_entry, platforms):
        # In tests, simply return an empty list (or you can simulate something).
        return []

    async def async_forward_entry_unload(self, config_entry, platform):
        # Simulate a successful unload.
        return True

    def async_update_entry(self, config_entry, data):
        config_entry.data = data


@pytest.fixture
def hass():
    return DummyHass()


@pytest.fixture
def dummy_config_entry():
    data = {
        "name": "Test Entry",
        "timeout": 60,
        "manual_refresh_only": True,
        "icon_color_mapping": "{}",
        "update_interval": 12,
        "council": "json",  # Use a valid module name
        "url": "http://example.com",
    }
    return DummyConfigEntry(data)


@pytest.mark.asyncio
async def test_household_bin_coordinator_retains_last_good_data(hass):
    # Create a dummy app with dynamic run output
    class DynamicUKBinCollectionApp:
        def __init__(self):
            self.call_count = 0

        def set_args(self, args):
            pass

        def run(self):
            self.call_count += 1
            if self.call_count == 1:
                # First call: valid data
                return json.dumps({
                    "bins": [
                        {"type": "waste", "collectionDate": datetime.now().strftime("%d/%m/%Y")},
                    ]
                })
            else:
                # Second call: empty bins
                return json.dumps({"bins": []})

    dummy_app = DynamicUKBinCollectionApp()

    coordinator = HouseholdBinCoordinator(
        hass,
        dummy_app,
        name="Test Bin",
        timeout=2,
        update_interval=timedelta(minutes=5)
    )

    # First fetch - stores valid data
    first_data = await coordinator._async_update_data()
    assert "waste" in first_data

    # Second fetch - empty, should fall back to previous data
    second_data = await coordinator._async_update_data()
    assert second_data == first_data  # Confirm fallback occurred


# --- Test async_setup ---
@pytest.mark.asyncio
async def test_async_setup_success(hass):
    # Call async_setup with a dummy config
    config = {"uk_bin_collection": {}}
    result = await async_setup(hass, config)
    assert result is True
    # Check that the integration data was initialized.
    assert DOMAIN in hass.data


@pytest.mark.asyncio
async def test_manual_refresh_no_entry(hass):
    # Call async_setup to register the service.
    config = {"uk_bin_collection": {}}
    await async_setup(hass, config)
    # Get the manual refresh service.
    service_func = hass.services.registrations.get((DOMAIN, "manual_refresh"))
    # Create a dummy call with no entry_id.
    dummy_call = MagicMock()
    dummy_call.data = {}
    # Capture log output or simply run the service call.
    await service_func(dummy_call)
    # You might check logs to verify the error was logged.


# --- Test async_migrate_entry ---
@pytest.mark.asyncio
async def test_async_migrate_entry_version_1(hass, dummy_config_entry):
    dummy_config_entry.version = 1
    # Remove update_interval to test migration defaults.
    dummy_config_entry.data.pop("update_interval", None)
    result = await async_migrate_entry(hass, dummy_config_entry)
    assert result is True
    # Now update_interval should be set to 12.
    assert dummy_config_entry.data["update_interval"] == 12


@pytest.mark.asyncio
async def test_async_migrate_entry_no_migration(hass, dummy_config_entry):
    dummy_config_entry.version = 2
    result = await async_migrate_entry(hass, dummy_config_entry)
    assert result is True


# --- Test async_setup_entry ---
@pytest.mark.asyncio
async def test_async_setup_entry_success(hass, dummy_config_entry):
    # Ensure hass.data[DOMAIN] is initialized.
    hass.data.setdefault(DOMAIN, {})

    # Patch the UKBinCollectionApp in the integration's namespace.
    with patch(
        "custom_components.uk_bin_collection.UKBinCollectionApp",
        return_value=DummyUKBinCollectionApp(),
    ):
        result = await async_setup_entry(hass, dummy_config_entry)
        assert result is True
        # Verify that the coordinator was stored in hass.data.
        assert dummy_config_entry.entry_id in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_setup_entry_missing_name(hass, dummy_config_entry):
    # Remove "name" to force a failure.
    dummy_config_entry.data.pop("name")
    with pytest.raises(ConfigEntryNotReady):
        await async_setup_entry(hass, dummy_config_entry)


# --- Test async_unload_entry ---
@pytest.mark.asyncio
async def test_async_unload_entry_success(hass, dummy_config_entry):
    # Prepopulate hass.data with a dummy coordinator.
    hass.data.setdefault(DOMAIN, {})[dummy_config_entry.entry_id] = {
        "coordinator": "dummy"
    }
    result = await async_unload_entry(hass, dummy_config_entry)
    assert result is True
    # The coordinator should have been removed.
    assert dummy_config_entry.entry_id not in hass.data[DOMAIN]


# --- Test build_ukbcd_args ---
def test_build_ukbcd_args_excludes_keys():
    config_data = {
        "council": "Test Council",
        "url": "http://example.com",
        "skip_get_url": "should be excluded",
        "custom_arg": "value",
    }
    args = build_ukbcd_args(config_data)
    # Check that the first two arguments are the council and url.
    assert args[0] == "Test Council"
    assert args[1] == "http://example.com"
    # The custom_arg should be included, but skip_get_url should not.
    args_str = " ".join(args)
    assert "--custom_arg=value" in args_str
    assert "skip_get_url" not in args_str


# --- Test HouseholdBinCoordinator update ---
@pytest.mark.asyncio
async def test_household_bin_coordinator_update(hass):
    # Create a dummy app whose run method returns valid JSON.
    dummy_app = DummyUKBinCollectionApp()
    coordinator = HouseholdBinCoordinator(
        hass, dummy_app, name="Test Bin", timeout=1, update_interval=timedelta(hours=1)
    )
    # Test the _async_update_data method.
    data = await coordinator._async_update_data()
    # Expect the data to be a dict with at least one bin type.
    assert isinstance(data, dict)
    assert "waste" in data or "recycling" in data


def test_process_bin_data_valid():
    # Test process_bin_data with valid bin data.
    now_str = datetime.now().strftime("%d/%m/%Y")
    data = {
        "bins": [
            {"type": "waste", "collectionDate": now_str},
            {"type": "recycling", "collectionDate": now_str},
        ]
    }
    processed = HouseholdBinCoordinator.process_bin_data(data)
    # Both bins should be in the processed output.
    assert "waste" in processed
    assert "recycling" in processed


def test_process_bin_data_invalid():
    # Test process_bin_data with missing keys and malformed date.
    data = {
        "bins": [
            {"type": None, "collectionDate": "bad_date"},
            {"collectionDate": "01/01/2025"},
        ]
    }
    processed = HouseholdBinCoordinator.process_bin_data(data)
    # Should be empty because data was invalid.
    assert processed == {}
