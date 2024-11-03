import asyncio
import json
from datetime import datetime, timedelta
from json import JSONDecodeError
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.uk_bin_collection.const import DOMAIN
from custom_components.uk_bin_collection.sensor import (
    HouseholdBinCoordinator,
    UKBinCollectionAttributeSensor,
    UKBinCollectionDataSensor,
    UKBinCollectionRawJSONSensor,
    async_setup_entry,
    get_latest_collection_info,
)

import logging
logging.basicConfig(level=logging.DEBUG)

from .common_utils import MockConfigEntry

# Mock Data
MOCK_BIN_COLLECTION_DATA = {
    "bins": [
        {"type": "General Waste", "collectionDate": "15/10/2023"},
        {"type": "Recycling", "collectionDate": "16/10/2023"},
        {"type": "Garden Waste", "collectionDate": "17/10/2023"},
    ]
}

MOCK_PROCESSED_DATA = {
    "General Waste": "15/10/2023",
    "Recycling": "16/10/2023",
    "Garden Waste": "17/10/2023",
}


# Fixtures
@pytest.fixture(autouse=True)
def expected_lingering_timers():
    """Allow lingering timers in this test."""
    return True


@pytest.fixture(autouse=True)
def mock_dt_now():
    with patch(
        "homeassistant.util.dt.now",
        return_value=datetime(2023, 10, 14, tzinfo=dt_util.DEFAULT_TIME_ZONE),
    ):
        yield


@pytest.fixture
def mock_config_entry():
    """Create a mock ConfigEntry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Entry",
        data={
            "name": "Test Name",
            "council": "Test Council",
            "url": "https://example.com",
            "timeout": 60,
            "icon_color_mapping": "{}",
        },
        entry_id="test",
        unique_id="test_unique_id",
    )


@pytest.fixture
def setup_coordinator(hass, mock_config_entry):
    """Fixture to set up the HouseholdBinCoordinator with mocked dependencies."""
    # Initialize hass.data
    hass.data = {}

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        # Mock async_add_executor_job correctly
        with patch.object(
            hass,
            "async_add_executor_job",
            new=AsyncMock(return_value=mock_app_instance.run.return_value),
        ):
            # Create the coordinator
            coordinator = HouseholdBinCoordinator(
                hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
            )

            yield coordinator


# Tests
def test_get_latest_collection_info(freezer):
    """Test processing of bin collection data."""
    freezer.move_to("2023-10-14")
    processed_data = get_latest_collection_info(MOCK_BIN_COLLECTION_DATA)
    assert processed_data == MOCK_PROCESSED_DATA


def test_get_latest_collection_info_empty():
    """Test processing when data is empty."""
    processed_data = get_latest_collection_info({"bins": []})
    assert processed_data == {}


def test_get_latest_collection_info_past_dates(freezer):
    """Test processing when all dates are in the past."""
    freezer.move_to("2023-10-14")
    past_date = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": past_date},
        ]
    }
    processed_data = get_latest_collection_info(data)
    assert processed_data == {}  # No future dates


def test_get_latest_collection_info_duplicate_bin_types(freezer):
    """Test processing when duplicate bin types are present."""
    freezer.move_to("2023-10-14")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "15/10/2023"},
            {"type": "General Waste", "collectionDate": "16/10/2023"},  # Later date
        ]
    }
    expected = {
        "General Waste": "15/10/2023",  # Should take the earliest future date
    }
    processed_data = get_latest_collection_info(data)
    assert processed_data == expected


def test_unique_id_uniqueness(hass, mock_config_entry):
    """Test that each sensor has a unique ID."""
    coordinator = MagicMock()
    coordinator.name = "Test Name"
    coordinator.data = MOCK_PROCESSED_DATA

    sensor1 = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )
    sensor2 = UKBinCollectionDataSensor(
        coordinator, "Recycling", "test_recycling", "{}"
    )

    assert sensor1.unique_id == "test_general_waste"
    assert sensor2.unique_id == "test_recycling"
    assert sensor1.unique_id != sensor2.unique_id


@pytest.mark.asyncio
async def test_async_setup_entry(hass, mock_config_entry):
    """Test setting up the sensor platform."""
    # Initialize mock_config_entry with necessary data
    mock_config_entry.data = {
        "name": "Test Name",
        "council": "Test Council",
        "url": "http://testurl.com",
        "timeout": 60,
        "icon_color_mapping": json.dumps(
            {
                "General Waste": {"icon": "mdi:trash-can", "color": "grey"},
                "Recycling": {"icon": "mdi:recycle", "color": "green"},
                "Garden Waste": {"icon": "mdi:flower", "color": "brown"},
            }
        ),
    }
    mock_config_entry.entry_id = "test_entry_id"

    # Ensure hass.data is an empty dictionary to simulate a new setup
    hass.data = {}

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        # Mock run method to return JSON data for testing
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        # Mock async_add_executor_job correctly
        with patch.object(
            hass,
            "async_add_executor_job",
            new=AsyncMock(return_value=mock_app_instance.run.return_value),
        ):
            # Mock async_add_entities as an AsyncMock
            async_add_entities = AsyncMock()

            # Call async_setup_entry to initialize setup
            await async_setup_entry(hass, mock_config_entry, async_add_entities)

            # Verify async_add_entities was called once
            assert async_add_entities.call_count == 1

            # Retrieve the list of entities that were added
            entities = async_add_entities.call_args[0][0]

            # Check the number of entities (6 per bin type + 1 raw JSON sensor)
            # 3 bin types * 6 entities each = 18 + 1 = 19
            assert len(entities) == 19, f"Expected 19 entities, got {len(entities)}"

            # Verify data was set in coordinator
            coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
            assert coordinator.data is not None, "Coordinator data should not be None."
            assert (
                coordinator.data == MOCK_PROCESSED_DATA
            ), "Coordinator data does not match expected values."

            # Optionally, verify that last_update_success is True
            assert (
                coordinator.last_update_success is True
            ), "Coordinator update was not successful."


@pytest.mark.asyncio
async def test_coordinator_fetch(setup_coordinator):
    """Test the data fetch by the coordinator."""
    coordinator = setup_coordinator

    # Perform the first refresh
    await coordinator.async_config_entry_first_refresh()

    # Verify data was set correctly
    assert (
        coordinator.data == MOCK_PROCESSED_DATA
    ), "Coordinator data does not match expected values."

    # Optionally, verify that last_update_success is True
    assert (
        coordinator.last_update_success is True
    ), "Coordinator update was not successful."


@pytest.mark.asyncio
async def test_bin_sensor(hass, mock_config_entry):
    """Test the main bin sensor."""
    # Initialize hass.data
    hass.data = {}

    # Patch UKBinCollectionApp
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        # Mock run method to return JSON data for testing
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        # Mock async_add_executor_job correctly
        with patch.object(
            hass,
            "async_add_executor_job",
            new=AsyncMock(return_value=mock_app_instance.run.return_value),
        ):
            # Create the coordinator
            coordinator = HouseholdBinCoordinator(
                hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
            )

            # Perform the first refresh
            await coordinator.async_config_entry_first_refresh()

    # Create a bin sensor
    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )

    # Access properties
    assert sensor.name == "Test Name General Waste"
    assert sensor.unique_id == "test_general_waste"

    # Assuming the current date is "2023-10-14" as set by freezer
    if sensor._days == 1:
        assert sensor.state == "Tomorrow"
    elif sensor._days == 0:
        assert sensor.state == "Today"
    else:
        assert sensor.state == f"In {sensor._days} days"

    assert sensor.icon == "mdi:trash-can"
    assert sensor.extra_state_attributes == {
        "colour": "black",
        "next_collection": "15/10/2023",
        "days": sensor._days,
    }


@pytest.mark.asyncio
async def test_raw_json_sensor(hass, mock_config_entry):
    """Test the raw JSON sensor."""
    # Initialize hass.data
    hass.data = {}

    # Patch UKBinCollectionApp
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        # Mock run method to return JSON data for testing
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        # Mock async_add_executor_job correctly
        with patch.object(
            hass,
            "async_add_executor_job",
            new=AsyncMock(return_value=mock_app_instance.run.return_value),
        ):
            # Create the coordinator
            coordinator = HouseholdBinCoordinator(
                hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
            )

            # Perform the first refresh
            await coordinator.async_config_entry_first_refresh()

    # Create the raw JSON sensor
    sensor = UKBinCollectionRawJSONSensor(coordinator, "test_raw_json", "Test Name")

    # Access properties
    assert sensor.name == "Test Name Raw JSON"
    assert sensor.unique_id == "test_raw_json"
    assert sensor.state == json.dumps(MOCK_PROCESSED_DATA)
    assert sensor.extra_state_attributes == {"raw_data": MOCK_PROCESSED_DATA}


@pytest.mark.asyncio
async def test_bin_sensor_custom_icon_color(hass, mock_config_entry):
    """Test bin sensor with custom icon and color."""
    icon_color_mapping = json.dumps(
        {"General Waste": {"icon": "mdi:delete", "color": "green"}}
    )

    # Initialize hass.data
    hass.data = {}

    # Patch UKBinCollectionApp
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        # Mock run method to return JSON data for testing
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        # Mock async_add_executor_job correctly
        with patch.object(
            hass,
            "async_add_executor_job",
            new=AsyncMock(return_value=mock_app_instance.run.return_value),
        ):
            # Create the coordinator
            coordinator = HouseholdBinCoordinator(
                hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
            )

            # Perform the first refresh
            await coordinator.async_config_entry_first_refresh()

    # Create a bin sensor with custom icon and color mapping
    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", icon_color_mapping
    )

    # Access properties
    assert sensor.icon == "mdi:delete"
    assert sensor.extra_state_attributes["colour"] == "green"


@pytest.mark.asyncio
async def test_bin_sensor_today_collection(hass, freezer, mock_config_entry):
    """Test bin sensor when collection is today."""
    freezer.move_to("2023-10-14")
    today_date = datetime.now().strftime("%d/%m/%Y")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": today_date},
        ]
    }

    # Initialize hass.data
    hass.data = {}

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        # Mock run method to return JSON data for testing
        mock_app_instance.run.return_value = json.dumps(data)

        # Mock async_add_executor_job correctly
        with patch.object(
            hass,
            "async_add_executor_job",
            new=AsyncMock(return_value=mock_app_instance.run.return_value),
        ):
            # Create the coordinator
            coordinator = HouseholdBinCoordinator(
                hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
            )

            # Perform the first refresh
            await coordinator.async_config_entry_first_refresh()

    # Create a bin sensor
    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )

    # Access properties
    assert sensor.state == "Today"


@pytest.mark.asyncio
async def test_bin_sensor_tomorrow_collection(hass, freezer, mock_config_entry):
    """Test bin sensor when collection is tomorrow."""
    freezer.move_to("2023-10-14")
    tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": tomorrow_date},
        ]
    }

    # Initialize hass.data
    hass.data = {}

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        # Mock run method to return JSON data for testing
        mock_app_instance.run.return_value = json.dumps(data)

        # Mock async_add_executor_job correctly
        with patch.object(
            hass,
            "async_add_executor_job",
            new=AsyncMock(return_value=mock_app_instance.run.return_value),
        ):
            # Create the coordinator
            coordinator = HouseholdBinCoordinator(
                hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
            )

            # Perform the first refresh
            await coordinator.async_config_entry_first_refresh()

    # Create a bin sensor
    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )

    # Access properties
    assert sensor.state == "Tomorrow"


@pytest.mark.asyncio
async def test_bin_sensor_partial_custom_icon_color(hass, mock_config_entry):
    """Test bin sensor with partial custom icon and color mappings."""
    icon_color_mapping = json.dumps(
        {"General Waste": {"icon": "mdi:delete", "color": "green"}}
    )

    # Modify MOCK_BIN_COLLECTION_DATA to include another bin type without custom mapping
    custom_data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "15/10/2023"},
            {"type": "Recycling", "collectionDate": "16/10/2023"},
        ]
    }

    # Initialize hass.data
    hass.data = {}

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(custom_data)

        # Mock async_add_executor_job correctly
        with patch.object(
            hass,
            "async_add_executor_job",
            new=AsyncMock(return_value=mock_app_instance.run.return_value),
        ):
            # Create the coordinator
            coordinator = HouseholdBinCoordinator(
                hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
            )

            # Perform the first refresh
            await coordinator.async_config_entry_first_refresh()

    # Create sensors for both bin types
    sensor_general = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", icon_color_mapping
    )
    sensor_recycling = UKBinCollectionDataSensor(
        coordinator, "Recycling", "test_recycling", icon_color_mapping
    )

    # Check custom mapping for General Waste
    assert sensor_general.icon == "mdi:delete"
    assert sensor_general.extra_state_attributes["colour"] == "green"

    # Check default mapping for Recycling
    assert sensor_recycling.icon == "mdi:recycle"
    assert sensor_recycling.extra_state_attributes["colour"] == "black"


def test_unique_id_uniqueness(hass, mock_config_entry):
    """Test that each sensor has a unique ID."""
    coordinator = MagicMock()
    coordinator.name = "Test Name"
    coordinator.data = MOCK_PROCESSED_DATA

    sensor1 = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )
    sensor2 = UKBinCollectionDataSensor(
        coordinator, "Recycling", "test_recycling", "{}"
    )

    assert sensor1.unique_id == "test_general_waste"
    assert sensor2.unique_id == "test_recycling"
    assert sensor1.unique_id != sensor2.unique_id


@pytest.fixture
def mock_dt_now_different_timezone():
    """Mock datetime.now with a different timezone."""
    with patch(
        "homeassistant.util.dt.now",
        return_value=datetime(2023, 10, 14, 12, 0, tzinfo=dt_util.UTC),
    ):
        yield


async def test_raw_json_sensor_invalid_data(hass, mock_config_entry):
    """Test raw JSON sensor with invalid data."""
    invalid_data = "Invalid JSON String"

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = invalid_data  # Not a valid JSON

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        # Attempt to refresh coordinator, which should NOT raise UpdateFailed
        await coordinator.async_refresh()

        # Verify that last_update_success is False
        assert coordinator.last_update_success is False

    # Create the raw JSON sensor
    sensor = UKBinCollectionRawJSONSensor(coordinator, "test_raw_json", "Test Name")

    # Since data fetch failed, sensor.state should reflect the failure
    assert sensor.state == json.dumps({})
    assert sensor.extra_state_attributes == {"raw_data": {}}
    assert sensor.available is False


def test_sensor_device_info(hass, mock_config_entry):
    """Test that sensors report correct device information."""
    coordinator = MagicMock()
    coordinator.name = "Test Name"
    coordinator.data = MOCK_PROCESSED_DATA

    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )

    expected_device_info = {
        "identifiers": {(DOMAIN, "test_general_waste")},
        "name": "Test Name General Waste",
        "manufacturer": "UK Bin Collection",
        "model": "Bin Sensor",
        "sw_version": "1.0",
    }
    assert sensor.device_info == expected_device_info


def test_get_latest_collection_info_duplicate_bin_types(freezer):
    """Test processing when duplicate bin types are present."""
    freezer.move_to("2023-10-14")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "15/10/2023"},
            {"type": "General Waste", "collectionDate": "16/10/2023"},  # Later date
        ]
    }
    expected = {
        "General Waste": "15/10/2023",  # Should take the earliest future date
    }
    processed_data = get_latest_collection_info(data)
    assert processed_data == expected


@pytest.mark.asyncio
async def test_coordinator_timeout_error(hass, mock_config_entry):
    """Test coordinator handles timeout errors correctly."""
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        # Simulate run raising TimeoutError
        mock_app_instance.run.side_effect = asyncio.TimeoutError("Request timed out")

        # Mock async_add_executor_job to raise TimeoutError
        hass.async_add_executor_job = AsyncMock(
            side_effect=mock_app_instance.run.side_effect
        )

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=1
        )

        # Expect ConfigEntryNotReady instead of UpdateFailed
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await coordinator.async_config_entry_first_refresh()

        assert "Timeout while updating data" in str(exc_info.value)


@pytest.mark.asyncio
async def test_coordinator_json_decode_error(hass, mock_config_entry):
    """Test coordinator handles JSON decode errors correctly."""
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        # Simulate run returning invalid JSON
        mock_app_instance.run.return_value = "Invalid JSON String"

        # Mock async_add_executor_job to raise JSONDecodeError
        def side_effect(*args, **kwargs):
            raise JSONDecodeError("Expecting value", "Invalid JSON String", 0)

        hass.async_add_executor_job = AsyncMock(side_effect=side_effect)

        # Initialize hass.data
        hass.data = {}

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        # Expect ConfigEntryNotReady instead of UpdateFailed
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await coordinator.async_config_entry_first_refresh()

        assert "JSON decode error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_coordinator_general_exception(hass, mock_config_entry):
    """Test coordinator handles general exceptions correctly."""
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        # Simulate run raising a general exception
        mock_app_instance.run.side_effect = Exception("General error")

        # Mock async_add_executor_job to raise the exception
        hass.async_add_executor_job = AsyncMock(
            side_effect=mock_app_instance.run.side_effect
        )

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        # Expect ConfigEntryNotReady instead of UpdateFailed
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await coordinator.async_config_entry_first_refresh()

        assert "Unexpected error" in str(exc_info.value)


def test_get_latest_collection_info_duplicate_bin_types(freezer):
    """Test processing when duplicate bin types are present with different dates."""
    freezer.move_to("2023-10-14")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "15/10/2023"},
            {"type": "General Waste", "collectionDate": "14/10/2023"},  # Earlier date
        ]
    }
    expected = {
        "General Waste": "14/10/2023",  # Should take the earliest future date
    }
    processed_data = get_latest_collection_info(data)
    assert processed_data == expected


def test_get_latest_collection_info_past_dates(freezer):
    """Test processing when all dates are in the past."""
    freezer.move_to("2023-10-14")
    past_date = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": past_date},
            {"type": "Recycling", "collectionDate": past_date},
        ]
    }
    processed_data = get_latest_collection_info(data)
    assert processed_data == {}  # No future dates should be included


def test_get_latest_collection_info_missing_fields(freezer):
    """Test processing when some bins are missing required fields."""
    freezer.move_to("2023-10-14")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "15/10/2023"},
            {"collectionDate": "16/10/2023"},  # Missing 'type'
            {"type": "Recycling"},  # Missing 'collectionDate'
        ]
    }
    expected = {
        "General Waste": "15/10/2023",
    }
    processed_data = get_latest_collection_info(data)
    assert processed_data == expected


def test_get_latest_collection_info_invalid_date_format(freezer):
    """Test processing when bins have invalid date formats."""
    freezer.move_to("2023-10-14")
    data = {
        "bins": [
            {
                "type": "General Waste",
                "collectionDate": "2023-10-15",
            },  # Incorrect format
            {"type": "Recycling", "collectionDate": "16/13/2023"},  # Invalid month
        ]
    }
    processed_data = get_latest_collection_info(data)
    assert processed_data == {}  # Both entries should be skipped due to invalid dates


@pytest.mark.asyncio
async def test_bin_sensor_state_today(hass, mock_config_entry, freezer):
    """Test bin sensor when collection is today."""
    freezer.move_to("2023-10-14")
    today_date = datetime.now().strftime("%d/%m/%Y")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": today_date},
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(data)

        # Mock async_add_executor_job to return the run method's return value
        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )
    sensor.apply_values()

    assert sensor.state == "Today"
    assert sensor.available is True
    assert sensor.extra_state_attributes["days"] == 0


@pytest.mark.asyncio
async def test_bin_sensor_state_tomorrow(hass, mock_config_entry, freezer):
    """Test bin sensor when collection is tomorrow."""
    freezer.move_to("2023-10-14")
    tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    data = {
        "bins": [
            {"type": "Recycling", "collectionDate": tomorrow_date},
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(data)

        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(coordinator, "Recycling", "test_recycling", "{}")
    sensor.apply_values()

    assert sensor.state == "Tomorrow"
    assert sensor.available is True
    assert sensor.extra_state_attributes["days"] == 1


@pytest.mark.asyncio
async def test_bin_sensor_state_in_days(hass, mock_config_entry, freezer):
    """Test bin sensor when collection is in multiple days."""
    freezer.move_to("2023-10-14")
    future_date = (datetime.now() + timedelta(days=5)).strftime("%d/%m/%Y")
    data = {
        "bins": [
            {"type": "Garden Waste", "collectionDate": future_date},
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(data)

        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator, "Garden Waste", "test_garden_waste", "{}"
    )
    sensor.apply_values()

    assert sensor.state == "In 5 days"
    assert sensor.available is True
    assert sensor.extra_state_attributes["days"] == 5


@pytest.mark.asyncio
async def test_bin_sensor_missing_data(hass, mock_config_entry):
    """Test bin sensor when bin data is missing."""
    data = {
        "bins": [
            # No bins provided
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(data)

        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator, "Non-Existent Bin", "test_non_existent_bin", "{}"
    )
    sensor.apply_values()

    assert sensor.state == "Unknown"
    assert sensor.available is False
    assert sensor.extra_state_attributes["days"] is None
    assert sensor.extra_state_attributes["next_collection"] is None



@pytest.mark.asyncio
async def test_raw_json_sensor_invalid_data(hass, mock_config_entry):
    """Test raw JSON sensor with invalid data."""
    invalid_data = "Invalid JSON String"

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        # Simulate run returning invalid JSON
        mock_app_instance.run.return_value = invalid_data

        # Mock async_add_executor_job to raise JSONDecodeError
        def side_effect(*args, **kwargs):
            raise JSONDecodeError("Expecting value", invalid_data, 0)

        hass.async_add_executor_job = AsyncMock(side_effect=side_effect)

        # Initialize hass.data
        hass.data = {}

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        # Perform the first refresh and expect ConfigEntryNotReady
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await coordinator.async_config_entry_first_refresh()

        assert "JSON decode error" in str(exc_info.value)

        # At this point, last_update_success should be False
        assert not coordinator.last_update_success

        # Create the RawJSONSensor
        raw_json_sensor = UKBinCollectionRawJSONSensor(
            coordinator, "test_raw_json", "Test Name"
        )

        # Do not perform a successful update
        # Sensor's available should be False
        assert raw_json_sensor.state == "{}"
        assert raw_json_sensor.extra_state_attributes["raw_data"] == {}
        assert raw_json_sensor.available is False


@pytest.mark.asyncio
async def test_raw_json_sensor_valid_and_empty_data(hass, mock_config_entry):
    """Test raw JSON sensor with valid and empty data."""
    # Test with valid data
    valid_data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "15/10/2023"},
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(valid_data)

        # Mock async_add_executor_job to return valid JSON
        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        # Initialize hass.data
        hass.data = {}

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    raw_json_sensor = UKBinCollectionRawJSONSensor(
        coordinator, "test_raw_json_valid", "Test Name"
    )

    # Simulate coordinator update with valid data
    coordinator.async_set_updated_data(coordinator.data)

    assert raw_json_sensor.state == json.dumps(
        {
            "General Waste": "15/10/2023",
        }
    )
    assert raw_json_sensor.extra_state_attributes["raw_data"] == {
        "General Waste": "15/10/2023",
    }
    assert raw_json_sensor.available is True

    # Test with empty data
    empty_data = {}

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app_empty:
        mock_app_empty_instance = mock_app_empty.return_value
        mock_app_empty_instance.run.return_value = json.dumps(empty_data)

        # Mock async_add_executor_job to return empty JSON
        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_empty_instance.run.return_value
        )

        coordinator_empty = HouseholdBinCoordinator(
            hass, mock_app_empty_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator_empty.async_config_entry_first_refresh()

    raw_json_sensor_empty = UKBinCollectionRawJSONSensor(
        coordinator_empty, "test_raw_json_empty", "Test Name"
    )

    # Simulate coordinator update with empty data
    coordinator_empty.async_set_updated_data(coordinator_empty.data)

    assert raw_json_sensor_empty.state == "{}"
    assert raw_json_sensor_empty.extra_state_attributes["raw_data"] == {}
    assert raw_json_sensor_empty.available is True  # Because last_update_success=True


@pytest.mark.asyncio
async def test_data_sensor_missing_icon_or_color(hass, mock_config_entry):
    """Test data sensor uses default icon and color when mappings are missing."""
    icon_color_mapping = json.dumps(
        {
            "General Waste": {"icon": "mdi:trash-can"},  # Missing 'color'
            "Recycling": {"color": "green"},  # Missing 'icon'
            "Garden Waste": {},  # Missing both
        }
    )

    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "15/10/2023"},
            {"type": "Recycling", "collectionDate": "16/10/2023"},
            {"type": "Garden Waste", "collectionDate": "17/10/2023"},
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(data)

        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    # Test General Waste sensor (missing 'color')
    general_waste_sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", icon_color_mapping
    )
    # Simulate coordinator update
    coordinator.async_set_updated_data(coordinator.data)

    assert general_waste_sensor.icon == "mdi:trash-can"
    assert general_waste_sensor.color == "black"  # Default color

    # Test Recycling sensor (missing 'icon')
    recycling_sensor = UKBinCollectionDataSensor(
        coordinator, "Recycling", "test_recycling", icon_color_mapping
    )
    coordinator.async_set_updated_data(coordinator.data)

    assert recycling_sensor.icon == "mdi:recycle"  # Default icon based on bin type
    assert recycling_sensor.color == "green"

    # Test Garden Waste sensor (missing both)
    garden_waste_sensor = UKBinCollectionDataSensor(
        coordinator, "Garden Waste", "test_garden_waste", icon_color_mapping
    )
    coordinator.async_set_updated_data(coordinator.data)

    assert garden_waste_sensor.icon == "mdi:trash-can"  # Default icon based on bin type
    assert garden_waste_sensor.color == "black"

@pytest.mark.asyncio
async def test_attribute_sensor_with_complete_mappings(hass, mock_config_entry):
    """Test attribute sensor correctly applies icon and color from mappings."""
    icon_color_mapping = json.dumps(
        {
            "General Waste": {"icon": "mdi:trash-can", "color": "grey"},
        }
    )
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "15/10/2023"},
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(data)

        # Mock async_add_executor_job to return valid JSON
        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        # Initialize hass.data
        hass.data = {}

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    # Test Colour attribute sensor
    colour_sensor = UKBinCollectionAttributeSensor(
        coordinator,
        "General Waste",
        "test_general_waste_colour",
        "Colour",
        "test_general_waste",
        icon_color_mapping,
    )

    # Simulate coordinator update
    coordinator.async_set_updated_data(coordinator.data)

    assert colour_sensor.state == "grey"
    assert colour_sensor.icon == "mdi:trash-can"
    assert colour_sensor.color == "grey"


@pytest.mark.asyncio
async def test_data_sensor_color_property_missing_or_none(hass, mock_config_entry):
    """Test sensor's color property when color is missing or None."""
    # Case 1: Missing color in icon_color_mapping
    icon_color_mapping_missing_color = json.dumps(
        {
            "General Waste": {"icon": "mdi:trash-can"},
        }
    )
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "15/10/2023"},
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app_missing_color:
        mock_app_missing_color_instance = mock_app_missing_color.return_value
        mock_app_missing_color_instance.run.return_value = json.dumps(data)

        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_missing_color_instance.run.return_value
        )

        coordinator = HouseholdBinCoordinator(
            hass,
            mock_app_missing_color_instance,
            "Test Name",
            mock_config_entry,
            timeout=60,
        )

        await coordinator.async_config_entry_first_refresh()

    sensor_missing_color = UKBinCollectionDataSensor(
        coordinator,
        "General Waste",
        "test_general_waste_missing_color",
        icon_color_mapping_missing_color,
    )
    # Simulate coordinator update
    coordinator.async_set_updated_data(coordinator.data)

    assert sensor_missing_color.color == "black"  # Default color

    # Case 2: Color is None
    icon_color_mapping_none_color = json.dumps(
        {
            "Recycling": {"icon": "mdi:recycle", "color": None},
        }
    )
    data_none_color = {
        "bins": [
            {"type": "Recycling", "collectionDate": "16/10/2023"},
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app_none_color:
        mock_app_none_color_instance = mock_app_none_color.return_value
        mock_app_none_color_instance.run.return_value = json.dumps(data_none_color)

        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_none_color_instance.run.return_value
        )

        coordinator_none_color = HouseholdBinCoordinator(
            hass,
            mock_app_none_color_instance,
            "Test Name",
            mock_config_entry,
            timeout=60,
        )

        await coordinator_none_color.async_config_entry_first_refresh()

    sensor_none_color = UKBinCollectionDataSensor(
        coordinator_none_color,
        "Recycling",
        "test_recycling_none_color",
        icon_color_mapping_none_color,
    )
    # Simulate coordinator update
    coordinator_none_color.async_set_updated_data(coordinator_none_color.data)

    assert (
        sensor_none_color.color == "black"
    )  # Should default to "black" if color is None


@pytest.mark.asyncio
async def test_unload_entry(hass):
    """Test unloading the config entry."""
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app, patch(
        "homeassistant.loader.async_get_integration", return_value=MagicMock()
    ):

        mock_app_instance = mock_app.return_value
        # Simulate run returning valid JSON
        mock_app_instance.run.return_value = json.dumps(
            {
                "bins": [
                    {"type": "General Waste", "collectionDate": "15/10/2023"},
                ]
            }
        )

        # Mock async_add_executor_job to return valid JSON
        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        # Initialize hass.data
        hass.data = {}

        # Create and add the config entry to hass
        mock_config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Name",
                "council": "Test Council",
                "url": "https://example.com",
                "timeout": 60,
                "icon_color_mapping": "{}",
            },
            entry_id="test_entry",
            unique_id="unique_id",
        )
        mock_config_entry.add_to_hass(hass)

        # Define a side effect for async_unload to remove the entry from hass.data
        async def async_unload_side_effect(entry_id):
            hass.data[DOMAIN].pop(entry_id, None)
            return True

        # Mock async_unload with the side effect
        hass.config_entries.async_unload = AsyncMock(side_effect=async_unload_side_effect)

        # Set up the entry
        async_add_entities = MagicMock()
        await async_setup_entry(hass, mock_config_entry, async_add_entities)
        await hass.async_block_till_done()

        # Verify coordinator is stored
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]

        # Unload the entry
        result = await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Assertions after unloading
        assert result is True
        assert mock_config_entry.state == ConfigEntryState.NOT_LOADED
        assert mock_config_entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_sensor_available_property(hass, mock_config_entry):
    """Test that sensor's available property reflects its state."""
    # Case 1: State is a valid string
    data_valid = {
        "bins": [
            {"type": "Recycling", "collectionDate": "16/10/2023"},
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app_valid:
        mock_app_valid_instance = mock_app_valid.return_value
        mock_app_valid_instance.run.return_value = json.dumps(data_valid)

        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_valid_instance.run.return_value
        )

        coordinator_valid = HouseholdBinCoordinator(
            hass, mock_app_valid_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator_valid.async_config_entry_first_refresh()

    sensor_valid = UKBinCollectionDataSensor(
        coordinator_valid, "Recycling", "test_recycling_available", "{}"
    )
    sensor_valid.apply_values()

    assert sensor_valid.available is True

    # Case 2: State is "Unknown"
    data_unknown = {
        "bins": [
            # No data for "Garden Waste"
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app_unknown:
        mock_app_unknown_instance = mock_app_unknown.return_value
        mock_app_unknown_instance.run.return_value = json.dumps(data_unknown)

        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_unknown_instance.run.return_value
        )

        coordinator_unknown = HouseholdBinCoordinator(
            hass, mock_app_unknown_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator_unknown.async_config_entry_first_refresh()

    sensor_unknown = UKBinCollectionDataSensor(
        coordinator_unknown, "Garden Waste", "test_garden_waste_unavailable", "{}"
    )
    sensor_unknown.apply_values()

    assert sensor_unknown.available is False


@pytest.mark.asyncio
async def test_coordinator_empty_data(hass, mock_config_entry):
    """Test coordinator handles empty data correctly."""
    empty_data = {"bins": []}

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(empty_data)

        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

        assert coordinator.data == {}
        assert coordinator.last_update_success is True


def test_coordinator_custom_update_interval(hass, mock_config_entry):
    """Test that coordinator uses a custom update interval."""
    custom_interval = timedelta(hours=6)
    coordinator = HouseholdBinCoordinator(
        hass, MagicMock(), "Test Name", mock_config_entry, timeout=60
    )
    coordinator.update_interval = custom_interval

    assert coordinator.update_interval == custom_interval


@pytest.mark.asyncio
async def test_async_setup_entry_missing_required_fields(hass):
    """Test setup with missing required configuration fields."""
    # Create a mock config entry missing 'name'
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            # "name" is missing
            "council": "Test Council",
            "url": "https://example.com",
            "timeout": 60,
            "icon_color_mapping": "{}",
        },
        entry_id="test_missing_name",
        unique_id="test_missing_name_unique_id",
    )

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app, patch(
        "homeassistant.loader.async_get_integration", return_value=MagicMock()
    ):
        mock_app_instance = mock_app.return_value
        # Simulate run returning valid JSON
        mock_app_instance.run.return_value = json.dumps(
            {
                "bins": [
                    {"type": "General Waste", "collectionDate": "15/10/2023"},
                ]
            }
        )

        # Mock async_add_executor_job to return valid JSON
        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        async_add_entities = MagicMock()

        # Initialize hass.data
        hass.data = {}

        # Add the config entry to hass
        mock_config_entry.add_to_hass(hass)

        # Set up the entry and expect ConfigEntryNotReady due to missing 'name'
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await async_setup_entry(hass, mock_config_entry, async_add_entities)

        # Adjust this assertion based on how your component handles missing 'name'
        assert "Missing 'name' in configuration." in str(exc_info.value)

        # Verify that entities were not added due to missing 'name'
        async_add_entities.assert_not_called()


@pytest.mark.asyncio
async def test_data_sensor_device_info(hass, mock_config_entry):
    """Test that data sensor reports correct device information."""
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "15/10/2023"},
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(data)

        icon_color_mapping = "{}"

        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator,
        "General Waste",
        "test_general_waste_device_info",
        icon_color_mapping,
    )
    sensor.apply_values()

    expected_device_info = {
        "identifiers": {(DOMAIN, "test_general_waste_device_info")},
        "name": "Test Name General Waste",
        "manufacturer": "UK Bin Collection",
        "model": "Bin Sensor",
        "sw_version": "1.0",
    }
    assert sensor.device_info == expected_device_info


@pytest.mark.asyncio
async def test_data_sensor_default_icon(hass, mock_config_entry):
    """Test data sensor uses default icon based on bin type when no mapping is provided."""
    data = {
        "bins": [
            {"type": "Unknown Bin", "collectionDate": "20/10/2023"},
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(data)

        # No icon_color_mapping provided
        icon_color_mapping = "{}"

        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator, "Unknown Bin", "test_unknown_bin", icon_color_mapping
    )
    sensor.apply_values()

    assert sensor.icon == "mdi:delete"
    assert sensor.color == "black"


def test_coordinator_update_interval(hass, mock_config_entry):
    """Test that coordinator uses the correct update interval."""
    coordinator = HouseholdBinCoordinator(
        hass, MagicMock(), "Test Name", mock_config_entry, timeout=60
    )
    assert coordinator.update_interval == timedelta(hours=12)


