# test_init.py
import asyncio
import json
import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed

# Import the functions and classes from your __init__.py file.
from custom_components.uk_bin_collection import (
    AddressMismatchError,
    BrowserUnavailableError,
    DependencyShadowingError,
    HouseholdBinCoordinator,
    SiteChanged,
    UpstreamAccessDenied,
    _COLLECTOR_RUN_STATES,
    _SOUTH_KESTEVEN_MIN_HA_TIMEOUT_SECONDS,
    async_migrate_entry,
    async_remove_entry,
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
        self.title = data.get("name", "")
        self.state = ConfigEntryState.SETUP_IN_PROGRESS
        self._unload_callbacks = []

    def async_on_unload(self, callback):
        """Mirror the ConfigEntry unload callback contract used by HA 2026.7."""
        self._unload_callbacks.append(callback)


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
    def __init__(self):
        self.update_calls = []
        self.unload_platform_calls = []

    async def async_forward_entry_setups(self, config_entry, platforms):
        # In tests, simply return an empty list (or you can simulate something).
        return []

    async def async_unload_platforms(self, config_entry, platforms):
        """Mirror Home Assistant's aggregate platform-unload API."""
        self.unload_platform_calls.append((config_entry, platforms))
        return True

    def async_update_entry(self, config_entry, data, **kwargs):
        config_entry.data = data
        if "version" in kwargs:
            config_entry.version = kwargs["version"]
        if "title" in kwargs:
            config_entry.title = kwargs["title"]
        self.update_calls.append((config_entry, data, kwargs))


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
                return json.dumps(
                    {
                        "bins": [
                            {
                                "type": "waste",
                                "collectionDate": datetime.now().strftime("%d/%m/%Y"),
                            },
                        ]
                    }
                )
            else:
                # Second call: empty bins
                return json.dumps({"bins": []})

    dummy_app = DynamicUKBinCollectionApp()

    coordinator = HouseholdBinCoordinator(
        hass,
        dummy_app,
        name="Test Bin",
        timeout=2,
        update_interval=timedelta(minutes=5),
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
    assert dummy_config_entry.data["manual_refresh_only"] is True
    assert dummy_config_entry.version == 4


@pytest.mark.asyncio
async def test_async_migrate_entry_no_migration(hass, dummy_config_entry):
    dummy_config_entry.version = 4
    result = await async_migrate_entry(hass, dummy_config_entry)
    assert result is True
    assert hass.config_entries.update_calls == []


@pytest.mark.asyncio
async def test_async_migrate_entry_version_2_adds_manual_mode(hass, dummy_config_entry):
    dummy_config_entry.version = 2
    dummy_config_entry.data.pop("manual_refresh_only", None)

    assert await async_migrate_entry(hass, dummy_config_entry) is True
    assert dummy_config_entry.version == 4
    assert dummy_config_entry.data["manual_refresh_only"] is True


@pytest.mark.asyncio
async def test_async_migrate_entry_v3_south_kesteven(hass, dummy_config_entry):
    dummy_config_entry.version = 3
    dummy_config_entry.data.update(
        {
            "council": "SouthKestevenDistrictCouncil",
            "url": "https://pre.southkesteven.gov.uk/old",
            "house_number": "43",
            "manual_refresh_only": "true",
            "web_driver": "http://selenium:4444/",
        }
    )

    assert await async_migrate_entry(hass, dummy_config_entry) is True
    assert dummy_config_entry.version == 4
    assert dummy_config_entry.data["url"] == "https://www.southkesteven.gov.uk/binday"
    assert dummy_config_entry.data["number"] == "43"
    assert dummy_config_entry.data["skip_get_url"] is True
    assert dummy_config_entry.data["web_driver"] == "http://selenium:4444"


@pytest.mark.asyncio
async def test_async_migrate_entry_v3_normalizes_paon_and_whitespace(
    hass, dummy_config_entry
):
    dummy_config_entry.version = 3
    dummy_config_entry.data.update(
        {
            "council": "SouthKestevenDistrictCouncil",
            "postcode": "NG31 8XG",
            "paon": "The Cottage",
            "selenium_url": "  http://selenium:4444/  ",
        }
    )

    assert await async_migrate_entry(hass, dummy_config_entry) is True
    assert dummy_config_entry.data["number"] == "The Cottage"
    assert "paon" not in dummy_config_entry.data
    assert "selenium_url" not in dummy_config_entry.data
    assert dummy_config_entry.data["web_driver"] == "http://selenium:4444"


@pytest.mark.asyncio
async def test_async_migrate_entry_v3_removes_all_legacy_aliases(
    hass, dummy_config_entry
):
    dummy_config_entry.version = 3
    dummy_config_entry.data.update(
        {
            "house_number": "43",
            "paon": "must-not-remain",
            "selenium_url": "http://selenium-primary:4444/",
            "webdriver": "http://selenium-stale:4444/",
        }
    )

    assert await async_migrate_entry(hass, dummy_config_entry) is True
    assert dummy_config_entry.data["number"] == "43"
    assert dummy_config_entry.data["web_driver"] == "http://selenium-primary:4444"
    for legacy_key in ("house_number", "paon", "selenium_url", "webdriver"):
        assert legacy_key not in dummy_config_entry.data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("legacy_number_key", "legacy_driver_key"),
    [
        ("house_number", "selenium_url"),
        ("paon", "webdriver"),
    ],
)
async def test_async_migrate_entry_v3_uses_valid_aliases_when_canonical_is_whitespace(
    hass, dummy_config_entry, legacy_number_key, legacy_driver_key
):
    dummy_config_entry.version = 3
    dummy_config_entry.data.update(
        {
            "number": "   ",
            legacy_number_key: "  The Cottage  ",
            "web_driver": "  ",
            legacy_driver_key: "  http://selenium:4444/wd/hub/  ",
        }
    )

    assert await async_migrate_entry(hass, dummy_config_entry) is True
    assert dummy_config_entry.data["number"] == "The Cottage"
    assert dummy_config_entry.data["web_driver"] == "http://selenium:4444/wd/hub"
    for legacy_key in ("house_number", "paon", "selenium_url", "webdriver"):
        assert legacy_key not in dummy_config_entry.data


# --- Test async_setup_entry ---
@pytest.mark.asyncio
async def test_async_setup_entry_success(hass, dummy_config_entry):
    # Ensure hass.data[DOMAIN] is initialized.
    hass.data.setdefault(DOMAIN, {})

    # Patch the UKBinCollectionApp in the integration's namespace.
    with patch(
        "custom_components.uk_bin_collection.UKBinCollectionApp",
        return_value=DummyUKBinCollectionApp(),
    ), patch("custom_components.uk_bin_collection.ir.async_delete_issue"):
        result = await async_setup_entry(hass, dummy_config_entry)
        assert result is True
        # Verify that the coordinator was stored in hass.data.
        assert dummy_config_entry.entry_id in hass.data[DOMAIN]
        assert (
            hass.data[DOMAIN][dummy_config_entry.entry_id][
                "coordinator"
            ].update_interval
            is None
        )


@pytest.mark.asyncio
async def test_south_kesteven_collector_deadline_precedes_ha_timeout(hass):
    entry = DummyConfigEntry(
        {
            "name": "South Kesteven",
            "timeout": 10,
            "manual_refresh_only": True,
            "update_interval": 12,
            "council": "SouthKestevenDistrictCouncil",
            "url": "https://www.southkesteven.gov.uk/binday",
            "postcode": "ZZ99 9ZZ",
            "number": "Codex Test House",
            "web_driver": "http://selenium:4444",
            "skip_get_url": True,
        },
        version=4,
        entry_id="south-kesteven-timeout",
    )
    hass.data.setdefault(DOMAIN, {})

    with patch(
        "custom_components.uk_bin_collection.UKBinCollectionApp",
        return_value=DummyUKBinCollectionApp(),
    ), patch("custom_components.uk_bin_collection.ir.async_delete_issue"):
        assert await async_setup_entry(hass, entry) is True

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    assert coordinator.timeout == _SOUTH_KESTEVEN_MIN_HA_TIMEOUT_SECONDS
    assert coordinator.timeout > 90 + 30


@pytest.mark.asyncio
async def test_setup_unexpected_error_redacts_exception_text(
    hass, dummy_config_entry, caplog
):
    sentinel = "SECRET-POSTCODE-ZZ99-9ZZ"
    hass.data.setdefault(DOMAIN, {})
    caplog.set_level(logging.ERROR)

    with patch(
        "custom_components.uk_bin_collection.UKBinCollectionApp",
        side_effect=RuntimeError(sentinel),
    ):
        with pytest.raises(
            ConfigEntryNotReady,
            match=r"Unexpected integration setup error \(RuntimeError\)",
        ) as raised:
            await async_setup_entry(hass, dummy_config_entry)

    assert sentinel not in caplog.text
    assert sentinel not in str(raised.value)
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True


@pytest.mark.asyncio
async def test_setup_update_failed_redacts_exception_text(
    hass, dummy_config_entry, caplog
):
    sentinel = "SECRET-UPRN-100012345678"
    hass.data.setdefault(DOMAIN, {})
    caplog.set_level(logging.ERROR)

    with patch(
        "custom_components.uk_bin_collection.HouseholdBinCoordinator."
        "async_config_entry_first_refresh",
        side_effect=UpdateFailed(sentinel),
    ):
        with pytest.raises(
            ConfigEntryNotReady,
            match=r"Initial collection lookup failed \(UpdateFailed\)",
        ) as raised:
            await async_setup_entry(hass, dummy_config_entry)

    assert sentinel not in caplog.text
    assert sentinel not in str(raised.value)
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True
    assert _COLLECTOR_RUN_STATES not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_setup_entry_missing_name(hass, dummy_config_entry):
    # Remove "name" to force a failure.
    dummy_config_entry.data.pop("name")
    with pytest.raises(ConfigEntryError, match="Reconfigure"):
        await async_setup_entry(hass, dummy_config_entry)


# --- Test async_unload_entry ---
@pytest.mark.asyncio
async def test_async_unload_entry_success(hass, dummy_config_entry):
    # Prepopulate hass.data with a dummy coordinator.
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data[dummy_config_entry.entry_id] = {"coordinator": "dummy"}
    coordinator = HouseholdBinCoordinator(
        hass,
        DummyUKBinCollectionApp(),
        name="Test Bin",
        config_entry_id=dummy_config_entry.entry_id,
    )
    assert (
        domain_data[_COLLECTOR_RUN_STATES][dummy_config_entry.entry_id]
        is coordinator._run_state
    )

    result = await async_unload_entry(hass, dummy_config_entry)

    assert result is True
    assert dummy_config_entry.entry_id not in hass.data[DOMAIN]
    assert _COLLECTOR_RUN_STATES not in hass.data[DOMAIN]
    assert hass.config_entries.unload_platform_calls == [
        (dummy_config_entry, PLATFORMS)
    ]


@pytest.mark.asyncio
async def test_async_unload_entry_failure_retains_runtime_data(
    hass, dummy_config_entry
):
    coordinator = HouseholdBinCoordinator(
        hass,
        DummyUKBinCollectionApp(),
        name="Test Bin",
        config_entry_id=dummy_config_entry.entry_id,
    )
    hass.data[DOMAIN][dummy_config_entry.entry_id] = {"coordinator": coordinator}

    async def reject_unload(config_entry, platforms):
        assert config_entry is dummy_config_entry
        assert platforms == PLATFORMS
        return False

    hass.config_entries.async_unload_platforms = reject_unload

    assert await async_unload_entry(hass, dummy_config_entry) is False
    assert hass.data[DOMAIN][dummy_config_entry.entry_id]["coordinator"] is coordinator
    assert (
        hass.data[DOMAIN][_COLLECTOR_RUN_STATES][dummy_config_entry.entry_id]
        is coordinator._run_state
    )


@pytest.mark.asyncio
async def test_platform_forward_failure_cleans_registered_coordinator(
    hass, dummy_config_entry
):
    hass.data.setdefault(DOMAIN, {})

    async def fail_forward(config_entry, platforms):
        assert config_entry is dummy_config_entry
        assert platforms == PLATFORMS
        raise RuntimeError("platform setup failed")

    hass.config_entries.async_forward_entry_setups = fail_forward

    with patch(
        "custom_components.uk_bin_collection.UKBinCollectionApp",
        return_value=DummyUKBinCollectionApp(),
    ), patch("custom_components.uk_bin_collection.ir.async_delete_issue"):
        with pytest.raises(
            ConfigEntryNotReady,
            match=r"Unexpected integration setup error \(RuntimeError\)",
        ):
            await async_setup_entry(hass, dummy_config_entry)

    assert dummy_config_entry.entry_id not in hass.data[DOMAIN]
    assert _COLLECTOR_RUN_STATES not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_unload_defers_run_state_cleanup_until_executor_finishes():
    loop = asyncio.get_running_loop()
    pending_run = loop.create_future()

    class ControlledHass(DummyHass):
        def async_add_executor_job(self, func, *args, **kwargs):
            del func, args, kwargs
            return pending_run

    hass = ControlledHass()
    entry = DummyConfigEntry(
        {
            "name": "Test Entry",
            "council": "json",
            "url": "http://example.com",
        },
        version=4,
        entry_id="entry-active-unload",
    )
    coordinator = HouseholdBinCoordinator(
        hass,
        DummyUKBinCollectionApp(),
        name="Test Bin",
        timeout=0.01,
        config_entry_id=entry.entry_id,
    )
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    with pytest.raises(UpdateFailed, match="Timeout"):
        await coordinator._async_update_data()

    assert await async_unload_entry(hass, entry) is True
    assert entry.entry_id not in hass.data[DOMAIN]
    state = hass.data[DOMAIN][_COLLECTOR_RUN_STATES][entry.entry_id]
    assert state is coordinator._run_state
    assert state.discard_when_idle is True

    pending_run.set_result(json.dumps({"bins": []}))
    await asyncio.sleep(0)
    assert _COLLECTOR_RUN_STATES not in hass.data[DOMAIN]


# --- Test build_ukbcd_args ---
def test_build_ukbcd_args_uses_typed_contract():
    config_data = {
        "council": "Test Council",
        "url": "http://example.com",
        "skip_get_url": True,
        "local_browser": True,
        "headless": False,
        "postcode": "NG31 8XG",
        "number": "43",
        "usrn": "200012345",
        "web_driver": "http://selenium:4444/",
        "user_agent": "UKBCD contract test",
        "custom_arg": "value",
    }
    args = build_ukbcd_args(config_data)
    # Check that the first two arguments are the council and url.
    assert args[0] == "Test Council"
    assert args[1] == "http://example.com"
    assert "--postcode=NG31 8XG" in args
    assert "--number=43" in args
    assert "--usrn=200012345" in args
    assert "--web_driver=http://selenium:4444" in args
    assert "--user-agent=UKBCD contract test" in args
    assert "--skip_get_url" in args
    assert "--local_browser" in args
    assert "--not-headless" in args
    assert all("custom_arg" not in arg for arg in args)


@pytest.mark.asyncio
async def test_south_kesteven_missing_fields_is_non_retryable(hass):
    entry = DummyConfigEntry(
        {
            "name": "South Kesteven",
            "council": "SouthKestevenDistrictCouncil",
            "url": "https://www.southkesteven.gov.uk/binday",
        },
        version=4,
    )
    hass.data.setdefault(DOMAIN, {})

    with patch(
        "custom_components.uk_bin_collection._create_missing_configuration_issue"
    ):
        with pytest.raises(ConfigEntryError, match="postcode, number"):
            await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_south_kesteven_conflicting_browser_settings_require_reconfigure(hass):
    entry = DummyConfigEntry(
        {
            "name": "South Kesteven",
            "council": "SouthKestevenDistrictCouncil",
            "url": "https://www.southkesteven.gov.uk/binday",
            "postcode": "NG31 8XG",
            "number": "43",
            "web_driver": "http://selenium:4444",
            "local_browser": True,
        },
        version=4,
    )
    hass.data.setdefault(DOMAIN, {})

    with patch(
        "custom_components.uk_bin_collection._create_missing_configuration_issue"
    ):
        with pytest.raises(ConfigEntryError, match="disable local_browser"):
            await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_permanent_first_refresh_failure_releases_idle_run_state(
    hass, dummy_config_entry
):
    hass.data.setdefault(DOMAIN, {})
    with patch(
        "custom_components.uk_bin_collection.HouseholdBinCoordinator."
        "async_config_entry_first_refresh",
        side_effect=ConfigEntryError("permanent setup failure"),
    ):
        with pytest.raises(ConfigEntryError, match="permanent setup failure"):
            await async_setup_entry(hass, dummy_config_entry)

    assert _COLLECTOR_RUN_STATES not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_cancelled_first_refresh_releases_idle_run_state(
    hass, dummy_config_entry
):
    hass.data.setdefault(DOMAIN, {})

    with patch(
        "custom_components.uk_bin_collection.HouseholdBinCoordinator."
        "async_config_entry_first_refresh",
        side_effect=asyncio.CancelledError,
    ):
        with pytest.raises(asyncio.CancelledError):
            await async_setup_entry(hass, dummy_config_entry)

    assert _COLLECTOR_RUN_STATES not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_remove_entry_clears_repairs_and_runtime_state(hass):
    entry = DummyConfigEntry(
        {"name": "Removed bins", "council": "ExampleCouncil"},
        version=4,
        entry_id="removed-entry",
    )
    hass.data[DOMAIN] = {
        entry.entry_id: {"coordinator": object()},
        _COLLECTOR_RUN_STATES: {},
    }

    with patch(
        "custom_components.uk_bin_collection.ir.async_delete_issue"
    ) as delete_issue:
        await async_remove_entry(hass, entry)

    assert entry.entry_id not in hass.data[DOMAIN]
    assert _COLLECTOR_RUN_STATES not in hass.data[DOMAIN]
    assert {call.args[2] for call in delete_issue.call_args_list} == {
        "dependency_removed-entry",
        "missing_configuration_removed-entry",
        "browser_removed-entry",
    }


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


@pytest.mark.asyncio
async def test_successful_empty_lookup_clears_stale_runtime_repairs(hass):
    class EmptyApp:
        def run(self):
            return json.dumps({"bins": []})

    coordinator = HouseholdBinCoordinator(
        hass,
        EmptyApp(),
        name="Test Bin",
        config_entry_id="entry-recovered",
    )

    with patch(
        "custom_components.uk_bin_collection.ir.async_delete_issue"
    ) as delete_issue:
        assert await coordinator._async_update_data() == {}

    deleted_ids = {call.args[2] for call in delete_issue.call_args_list}
    assert deleted_ids == {
        "dependency_entry-recovered",
        "browser_entry-recovered",
    }


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


@pytest.mark.asyncio
async def test_dependency_shadowing_is_actionable_and_non_retryable(hass):
    class ShadowedDependencyApp:
        def run(self):
            raise DependencyShadowingError(
                "websocket resolved to /config/websocket/__init__.py"
            )

    coordinator = HouseholdBinCoordinator(
        hass,
        ShadowedDependencyApp(),
        name="Test Bin",
        config_entry_id="entry-1",
    )

    with patch(
        "custom_components.uk_bin_collection._create_dependency_issue"
    ) as issue, patch(
        "custom_components.uk_bin_collection.ir.async_delete_issue"
    ) as delete_issue:
        with pytest.raises(ConfigEntryError, match="missing or shadowed"):
            await coordinator._async_update_data()
    issue.assert_called_once()
    delete_issue.assert_called_once_with(hass, DOMAIN, "browser_entry-1")


@pytest.mark.asyncio
async def test_browser_unavailable_is_actionable_without_unexpected_traceback(
    hass, caplog
):
    class BrowserFailureApp:
        def run(self):
            raise BrowserUnavailableError("Unable to create the configured browser")

    coordinator = HouseholdBinCoordinator(
        hass,
        BrowserFailureApp(),
        name="Test Bin",
        config_entry_id="entry-browser",
    )

    with patch(
        "custom_components.uk_bin_collection._create_browser_issue"
    ) as issue, patch(
        "custom_components.uk_bin_collection.ir.async_delete_issue"
    ) as delete_issue:
        with pytest.raises(UpdateFailed, match="WebDriver is unavailable"):
            await coordinator._async_update_data()

    issue.assert_called_once()
    delete_issue.assert_called_once_with(hass, DOMAIN, "dependency_entry-browser")
    assert "Unexpected" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_exception", "message"),
    [
        (
            AddressMismatchError("not unique"),
            ConfigEntryError,
            "need to be corrected",
        ),
        (
            UpstreamAccessDenied("blocked"),
            UpdateFailed,
            "denied browser access",
        ),
        (
            SiteChanged("selector missing"),
            UpdateFailed,
            "supported layout",
        ),
    ],
)
async def test_expected_collector_errors_keep_distinct_ha_diagnostics(
    hass, error, expected_exception, message, caplog
):
    class TypedFailureApp:
        def run(self):
            raise error

    coordinator = HouseholdBinCoordinator(
        hass,
        TypedFailureApp(),
        name="Test Bin",
        config_entry_id="entry-transition",
    )

    with patch(
        "custom_components.uk_bin_collection.ir.async_delete_issue"
    ) as delete_issue:
        with pytest.raises(expected_exception, match=message):
            await coordinator._async_update_data()

    assert "Unexpected" not in caplog.text
    assert {call.args[2] for call in delete_issue.call_args_list} == {
        "dependency_entry-transition",
        "browser_entry-transition",
    }


@pytest.mark.asyncio
async def test_coordinator_logs_do_not_include_household_sentinels(hass, caplog):
    caplog.set_level(logging.DEBUG)
    sentinel_values = (
        "SECRET-POSTCODE",
        "SECRET-PAON",
        "100012345678",
        "200012345",
        "token=secret-query",
    )

    class RedactionApp:
        def run(self):
            return json.dumps(
                {
                    "postcode": sentinel_values[0],
                    "paon": sentinel_values[1],
                    "uprn": sentinel_values[2],
                    "usrn": sentinel_values[3],
                    "url": f"https://example.invalid/?{sentinel_values[4]}",
                    "bins": [
                        {
                            "type": "waste",
                            "collectionDate": datetime.now().strftime("%d/%m/%Y"),
                        }
                    ],
                }
            )

    coordinator = HouseholdBinCoordinator(hass, RedactionApp(), name="Test Bin")
    await coordinator._async_update_data()

    for sentinel in sentinel_values:
        assert sentinel not in caplog.text


@pytest.mark.asyncio
async def test_unexpected_coordinator_error_is_class_only(hass, caplog):
    sentinel = "SECRET-PAON-CODEX-TEST-HOUSE"
    caplog.set_level(logging.ERROR)

    class UnexpectedFailureApp:
        def run(self):
            raise RuntimeError(sentinel)

    coordinator = HouseholdBinCoordinator(hass, UnexpectedFailureApp(), name="Test Bin")

    with pytest.raises(
        UpdateFailed, match=r"Unexpected collector error \(RuntimeError\)"
    ) as raised:
        await coordinator._async_update_data()

    assert sentinel not in caplog.text
    assert sentinel not in str(raised.value)
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True


@pytest.mark.asyncio
async def test_coordinator_does_not_overlap_timed_out_executor_work():
    loop = asyncio.get_running_loop()
    pending_run = loop.create_future()

    class ControlledHass(DummyHass):
        def async_add_executor_job(self, func, *args, **kwargs):
            del func, args, kwargs
            return pending_run

    hass = ControlledHass()
    first_coordinator = HouseholdBinCoordinator(
        hass,
        DummyUKBinCollectionApp(),
        name="Test Bin",
        timeout=0.01,
        config_entry_id="entry-retry",
    )
    retry_coordinator = HouseholdBinCoordinator(
        hass,
        DummyUKBinCollectionApp(),
        name="Test Bin",
        timeout=0.01,
        config_entry_id="entry-retry",
    )

    with pytest.raises(UpdateFailed, match="Timeout"):
        await first_coordinator._async_update_data()

    # A new coordinator created by a setup retry/reload must observe the first
    # coordinator's still-running executor Future.
    assert first_coordinator._run_state is retry_coordinator._run_state
    assert (
        hass.data[DOMAIN][_COLLECTOR_RUN_STATES]["entry-retry"]
        is first_coordinator._run_state
    )
    assert first_coordinator._active_run is pending_run
    assert not pending_run.done()
    with pytest.raises(UpdateFailed, match="previous collector run"):
        await retry_coordinator._async_update_data()

    # The failed retry must not replace or clear the first in-flight marker.
    assert first_coordinator._active_run is pending_run

    pending_run.set_result(json.dumps({"bins": []}))
    await asyncio.sleep(0)
    assert first_coordinator._active_run is None
    assert retry_coordinator._active_run is None
