import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from json import JSONDecodeError
from unittest.mock import AsyncMock, MagicMock, patch, Mock

import pytest
from freezegun import freeze_time
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.core import ServiceCall
from custom_components.uk_bin_collection import (
    async_setup_entry as async_setup_entry_domain,
)
from custom_components.uk_bin_collection.sensor import (
    async_setup_entry as async_setup_entry_sensor,
)

from custom_components.uk_bin_collection.const import (
    DOMAIN,
    LOG_PREFIX,
    STATE_ATTR_COLOUR,
    STATE_ATTR_NEXT_COLLECTION,
    STATE_ATTR_DAYS,
)
from custom_components.uk_bin_collection.sensor import (
    UKBinCollectionAttributeSensor,
    UKBinCollectionDataSensor,
    UKBinCollectionRawJSONSensor,
    create_sensor_entities,
    load_icon_color_mapping,
)

from custom_components.uk_bin_collection import HouseholdBinCoordinator

logging.basicConfig(level=logging.DEBUG)

from .common_utils import MockConfigEntry

pytest_plugins = ["freezegun"]

# Mock Data
MOCK_BIN_COLLECTION_DATA = {
    "bins": [
        {"type": "General Waste", "collectionDate": "15/10/2023"},
        {"type": "Recycling", "collectionDate": "16/10/2023"},
        {"type": "Garden Waste", "collectionDate": "17/10/2023"},
    ]
}

MOCK_PROCESSED_DATA = {
    "General Waste": datetime.strptime("15/10/2023", "%d/%m/%Y").date(),
    "Recycling": datetime.strptime("16/10/2023", "%d/%m/%Y").date(),
    "Garden Waste": datetime.strptime("17/10/2023", "%d/%m/%Y").date(),
}


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
            "icon_color_mapping": {},
        },
        entry_id="test",
        unique_id="test_unique_id",
    )


# Tests
def test_process_bin_data(freezer):
    """Test processing of bin collection data."""
    freezer.move_to("2023-10-14")
    processed_data = HouseholdBinCoordinator.process_bin_data(MOCK_BIN_COLLECTION_DATA)
    # Convert dates to strings for comparison
    processed_data_str = {k: v.strftime("%Y-%m-%d") for k, v in processed_data.items()}
    expected_data_str = {
        k: v.strftime("%Y-%m-%d") for k, v in MOCK_PROCESSED_DATA.items()
    }
    assert processed_data_str == expected_data_str


def test_process_bin_data_empty():
    """Test processing when data is empty."""
    processed_data = HouseholdBinCoordinator.process_bin_data({"bins": []})
    assert processed_data == {}


def test_process_bin_data_past_dates(freezer):
    """Test processing when all dates are in the past."""
    freezer.move_to("2023-10-14")
    past_date = (datetime(2023, 10, 14) - timedelta(days=1)).strftime("%d/%m/%Y")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": past_date},
        ]
    }
    processed_data = HouseholdBinCoordinator.process_bin_data(data)
    assert processed_data == {}  # No future dates


def test_process_bin_data_duplicate_bin_types(freezer):
    """Test processing when duplicate bin types are present."""
    freezer.move_to("2023-10-14")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "15/10/2023"},
            {"type": "General Waste", "collectionDate": "16/10/2023"},  # Later date
        ]
    }
    expected = {
        "General Waste": date(2023, 10, 15),  # Should take the earliest future date
    }
    processed_data = HouseholdBinCoordinator.process_bin_data(data)
    assert processed_data == expected


def test_unique_id_uniqueness():
    """Test that each sensor has a unique ID."""
    coordinator = MagicMock()
    coordinator.name = "Test Name"
    coordinator.data = MOCK_PROCESSED_DATA

    sensor1 = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", {}
    )
    sensor2 = UKBinCollectionDataSensor(coordinator, "Recycling", "test_recycling", {})

    assert sensor1.unique_id == "test_general_waste"
    assert sensor2.unique_id == "test_recycling"
    assert sensor1.unique_id != sensor2.unique_id


@pytest.mark.asyncio
@freeze_time("2023-10-14")
async def test_async_setup_entry(hass, mock_config_entry):
    """Test setting up the sensor platform directly."""
    # 1) We need to fake the coordinator in hass.data
    hass.data = {}
    hass.data.setdefault(DOMAIN, {})

    # Create a mock coordinator (or real if you like)
    mock_coordinator = MagicMock()
    # Store it under the entry_id as normal domain code would do
    hass.data[DOMAIN][mock_config_entry.entry_id] = {"coordinator": mock_coordinator}

    # 2) Prepare a mock to track added entities
    async_add_entities = Mock()

    # 3) Patch sensor’s UKBinCollectionApp calls if needed
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps({"bins": []})

        with patch.object(
            hass,
            "async_add_executor_job",
            new_callable=AsyncMock,
            return_value=mock_app_instance.run.return_value,
        ):
            # 4) Now call the sensor setup function
            await async_setup_entry_sensor(hass, mock_config_entry, async_add_entities)

    # 5) Assert that sensor got set up
    assert async_add_entities.call_count == 1
    # ... any other assertions you want


@freeze_time("2023-10-14")
@pytest.mark.asyncio
async def test_coordinator_fetch(hass):
    """Test the data fetch by the coordinator."""
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        with patch.object(
            hass,
            "async_add_executor_job",
            new_callable=AsyncMock,
            return_value=mock_app_instance.run.return_value,
        ):
            coordinator = HouseholdBinCoordinator(
                hass, mock_app_instance, "Test Name", timeout=60
            )

            await coordinator.async_refresh()

    assert (
        coordinator.data == MOCK_PROCESSED_DATA
    ), "Coordinator data does not match expected values."
    assert (
        coordinator.last_update_success is True
    ), "Coordinator update was not successful."


@pytest.mark.asyncio
async def test_bin_sensor(hass, mock_config_entry):
    """Test the main bin sensor."""
    from freezegun import freeze_time

    hass.data = {}

    with freeze_time("2023-10-14"):
        with patch(
            "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
        ) as mock_app:
            mock_app_instance = mock_app.return_value
            mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

            with patch.object(
                hass,
                "async_add_executor_job",
                return_value=mock_app_instance.run.return_value,
            ):
                coordinator = HouseholdBinCoordinator(
                    hass, mock_app_instance, "Test Name", timeout=60
                )

                await coordinator.async_config_entry_first_refresh()

        sensor = UKBinCollectionDataSensor(
            coordinator, "General Waste", "test_general_waste", {}
        )

        assert sensor.name == "Test Name General Waste"
        assert sensor.unique_id == "test_general_waste"
        assert sensor.state == "Tomorrow"
        assert sensor.icon == "mdi:trash-can"
        assert sensor.extra_state_attributes == {
            "colour": "black",
            "next_collection": "15/10/2023",
            "days": 1,
        }


@freeze_time("2023-10-14")
@pytest.mark.asyncio
async def test_raw_json_sensor(hass, mock_config_entry):
    """Test the raw JSON sensor."""
    hass.data = {}

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        with patch.object(
            hass,
            "async_add_executor_job",
            new_callable=AsyncMock,
            return_value=mock_app_instance.run.return_value,
        ):
            coordinator = HouseholdBinCoordinator(
                hass, mock_app_instance, "Test Name", timeout=60
            )

            await coordinator.async_refresh()

    sensor = UKBinCollectionRawJSONSensor(coordinator, "test_raw_json", "Test Name")

    expected_state = json.dumps(
        {k: v.strftime("%d/%m/%Y") for k, v in MOCK_PROCESSED_DATA.items()}
    )

    assert sensor.name == "Test Name Raw JSON"
    assert sensor.unique_id == "test_raw_json"
    assert sensor.state == expected_state
    assert sensor.extra_state_attributes == {"raw_data": MOCK_PROCESSED_DATA}


@pytest.mark.asyncio
async def test_bin_sensor_custom_icon_color(hass, mock_config_entry):
    """Test bin sensor with custom icon and color."""
    icon_color_mapping = {"General Waste": {"icon": "mdi:delete", "color": "green"}}

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
                hass, mock_app_instance, "Test Name", timeout=60
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
    today_date = dt_util.now().strftime("%d/%m/%Y")
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
                hass, mock_app_instance, "Test Name", timeout=60
            )

            # Perform the first refresh
            await coordinator.async_config_entry_first_refresh()

    # Create a bin sensor
    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", {}
    )

    # Access properties
    assert sensor.state == "Today"


@pytest.mark.asyncio
async def test_bin_sensor_tomorrow_collection(hass, freezer, mock_config_entry):
    """Test bin sensor when collection is tomorrow."""
    freezer.move_to("2023-10-14")
    tomorrow_date = (dt_util.now() + timedelta(days=1)).strftime("%d/%m/%Y")
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
                hass, mock_app_instance, "Test Name", timeout=60
            )

            # Perform the first refresh
            await coordinator.async_config_entry_first_refresh()

    # Create a bin sensor
    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", {}
    )

    # Access properties
    assert sensor.state == "Tomorrow"


@pytest.mark.asyncio
async def test_bin_sensor_partial_custom_icon_color(hass, mock_config_entry):
    """Test bin sensor with partial custom icon and color mappings."""
    icon_color_mapping = {"General Waste": {"icon": "mdi:delete", "color": "green"}}

    # Modify json.dumps(MOCK_BIN_COLLECTION_DATA) to include another bin type without custom mapping
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
                hass, mock_app_instance, "Test Name", timeout=60
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
        coordinator, "General Waste", "test_general_waste", {}
    )
    sensor2 = UKBinCollectionDataSensor(coordinator, "Recycling", "test_recycling", {})

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
            hass, mock_app_instance, "Test Name", timeout=60
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
        coordinator, "General Waste", "test_general_waste", {}
    )

    expected_device_info = {
        "identifiers": {(DOMAIN, "test_general_waste")},
        "name": "Test Name General Waste",
        "manufacturer": "UK Bin Collection",
        "model": "Bin Sensor",
        "sw_version": "1.0",
    }
    assert sensor.device_info == expected_device_info


def process_bin_data_duplicate_bin_types(freezer):
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
    processed_data = HouseholdBinCoordinator.process_bin_data(data)
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
            hass, mock_app_instance, "Test Name", timeout=1
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
            hass, mock_app_instance, "Test Name", timeout=60
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
            hass, mock_app_instance, "Test Name", timeout=60
        )

        # Expect ConfigEntryNotReady instead of UpdateFailed
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await coordinator.async_config_entry_first_refresh()

        assert "Unexpected error" in str(exc_info.value)


def process_bin_data_duplicate_bin_types(freezer):
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
    processed_data = HouseholdBinCoordinator.process_bin_data(data)
    assert processed_data == expected


def process_bin_data_past_dates(freezer):
    """Test processing when all dates are in the past."""
    freezer.move_to("2023-10-14")
    past_date = (dt_util.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": past_date},
            {"type": "Recycling", "collectionDate": past_date},
        ]
    }
    processed_data = HouseholdBinCoordinator.process_bin_data(data)
    assert processed_data == {}  # No future dates should be included


def process_bin_data_missing_fields(freezer):
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
    processed_data = HouseholdBinCoordinator.process_bin_data(data)
    assert processed_data == expected


def process_bin_data_invalid_date_format(freezer):
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
    processed_data = HouseholdBinCoordinator.process_bin_data(data)
    assert processed_data == {}  # Both entries should be skipped due to invalid dates


@pytest.mark.asyncio
async def test_bin_sensor_state_today(hass, mock_config_entry, freezer):
    """Test bin sensor when collection is today."""
    freezer.move_to("2023-10-14")
    today_date = dt_util.now().strftime("%d/%m/%Y")
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
            hass, mock_app_instance, "Test Name", timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", {}
    )

    assert sensor.state == "Today"
    assert sensor.available is True
    assert sensor.extra_state_attributes["days"] == 0


@pytest.mark.asyncio
async def test_bin_sensor_state_tomorrow(hass, mock_config_entry, freezer):
    """Test bin sensor when collection is tomorrow."""
    freezer.move_to("2023-10-14")
    tomorrow_date = (dt_util.now() + timedelta(days=1)).strftime("%d/%m/%Y")
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
            hass, mock_app_instance, "Test Name", timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(coordinator, "Recycling", "test_recycling", {})

    assert sensor.state == "Tomorrow"
    assert sensor.available is True
    assert sensor.extra_state_attributes["days"] == 1


@pytest.mark.asyncio
async def test_bin_sensor_state_in_days(hass, mock_config_entry, freezer):
    """Test bin sensor when collection is in multiple days."""
    freezer.move_to("2023-10-14")
    future_date = (dt_util.now() + timedelta(days=5)).strftime("%d/%m/%Y")
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
            hass, mock_app_instance, "Test Name", timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator, "Garden Waste", "test_garden_waste", {}
    )

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
            hass, mock_app_instance, "Test Name", timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator, "Non-Existent Bin", "test_non_existent_bin", {}
    )

    assert sensor.state == "Unknown"
    assert sensor.available is False
    assert sensor.extra_state_attributes["days"] is None
    assert sensor.extra_state_attributes["next_collection"] is None


@freeze_time("2023-10-14")
@pytest.mark.asyncio
async def test_raw_json_sensor_invalid_data(hass, mock_config_entry):
    """Test raw JSON sensor with invalid data."""
    invalid_data = "Invalid JSON String"

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = invalid_data

        def side_effect(*args, **kwargs):
            raise JSONDecodeError("Expecting value", invalid_data, 0)

        with patch.object(hass, "async_add_executor_job", side_effect=side_effect):
            coordinator = HouseholdBinCoordinator(
                hass, mock_app_instance, "Test Name", timeout=60
            )

            await coordinator.async_refresh()

    assert not coordinator.last_update_success

    raw_json_sensor = UKBinCollectionRawJSONSensor(
        coordinator, "test_raw_json", "Test Name"
    )

    assert raw_json_sensor.state == "{}"
    assert raw_json_sensor.extra_state_attributes["raw_data"] == {}
    assert raw_json_sensor.available is False


@pytest.mark.asyncio
async def test_sensor_available_property(hass, mock_config_entry):
    """Test that sensor's available property reflects its state."""
    # Case 1: State is a valid string
    data_valid = {
        "bins": [
            {"type": "Recycling", "collectionDate": "16/10/2023"},
        ]
    }
    processed_data_valid = {
        "Recycling": datetime.strptime("16/10/2023", "%d/%m/%Y").date(),
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app_valid:
        mock_app_valid_instance = mock_app_valid.return_value
        mock_app_valid_instance.run.return_value = json.dumps(data_valid)

        with patch.object(
            hass,
            "async_add_executor_job",
            return_value=mock_app_valid_instance.run.return_value,
        ):
            coordinator_valid = HouseholdBinCoordinator(
                hass, mock_app_valid_instance, "Test Name", timeout=60
            )

            await coordinator_valid.async_refresh()

    sensor_valid = UKBinCollectionDataSensor(
        coordinator_valid, "Recycling", "test_recycling_available", {}
    )

    assert sensor_valid.available is True

    # Case 2: State is "Unknown"
    data_unknown = {"bins": []}

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app_unknown:
        mock_app_unknown_instance = mock_app_unknown.return_value
        mock_app_unknown_instance.run.return_value = json.dumps(data_unknown)

        with patch.object(
            hass,
            "async_add_executor_job",
            return_value=mock_app_unknown_instance.run.return_value,
        ):
            coordinator_unknown = HouseholdBinCoordinator(
                hass, mock_app_unknown_instance, "Test Name", timeout=60
            )

            await coordinator_unknown.async_refresh()

    sensor_unknown = UKBinCollectionDataSensor(
        coordinator_unknown, "Garden Waste", "test_garden_waste_unavailable", {}
    )

    assert sensor_unknown.available is False


@pytest.mark.asyncio
async def test_data_sensor_missing_icon_or_color(hass, mock_config_entry):
    """Test data sensor uses default icon and color when mappings are missing."""
    icon_color_mapping = {
        "General Waste": {"icon": "mdi:trash-can"},  # Missing 'color'
        "Recycling": {"color": "green"},  # Missing 'icon'
        "Garden Waste": {},  # Missing both
    }

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
            hass, mock_app_instance, "Test Name", timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    # Test General Waste sensor (missing 'color')
    general_waste_sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", icon_color_mapping
    )
    # Simulate coordinator update
    coordinator.async_set_updated_data(coordinator.data)

    assert general_waste_sensor.icon == "mdi:trash-can"
    assert general_waste_sensor._color == "black"  # Default color

    # Test Recycling sensor (missing 'icon')
    recycling_sensor = UKBinCollectionDataSensor(
        coordinator, "Recycling", "test_recycling", icon_color_mapping
    )
    coordinator.async_set_updated_data(coordinator.data)

    assert recycling_sensor.icon == "mdi:recycle"  # Default icon based on bin type
    assert recycling_sensor._color == "green"

    # Test Garden Waste sensor (missing both)
    garden_waste_sensor = UKBinCollectionDataSensor(
        coordinator, "Garden Waste", "test_garden_waste", icon_color_mapping
    )
    coordinator.async_set_updated_data(coordinator.data)

    assert garden_waste_sensor.icon == "mdi:trash-can"  # Default icon based on bin type
    assert garden_waste_sensor._color == "black"


@pytest.mark.asyncio
async def test_attribute_sensor_with_complete_mappings(hass, mock_config_entry):
    """Test attribute sensor correctly applies icon and color from mappings."""
    icon_color_mapping = {"General Waste": {"icon": "mdi:trash-can", "color": "grey"}}
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
            hass, mock_app_instance, "Test Name", timeout=60
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
    assert colour_sensor._color == "grey"


@pytest.mark.asyncio
async def test_data_sensor_color_property_missing_or_none(hass, mock_config_entry):
    """Test sensor's color property when color is missing or None."""
    # Case 1: Missing color in icon_color_mapping
    icon_color_mapping_missing_color = {
        "General Waste": {"icon": "mdi:trash-can"},
    }
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

    assert sensor_missing_color._color == "black"  # Default color

    # Case 2: Color is None
    icon_color_mapping_none_color = {
        "Recycling": {"icon": "mdi:recycle", "color": None},
    }

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
        sensor_none_color._color == "black"
    )  # Should default to "black" if color is None


@freeze_time("2023-10-14")
@pytest.mark.asyncio
async def test_sensor_available_property(hass, mock_config_entry):
    """Test that sensor's available property reflects its state."""
    # Case 1: State is a valid string
    data_valid = {
        "bins": [
            {"type": "Recycling", "collectionDate": "16/10/2023"},
        ]
    }
    processed_data_valid = {
        "Recycling": datetime.strptime("16/10/2023", "%d/%m/%Y").date(),
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app_valid:
        mock_app_valid_instance = mock_app_valid.return_value
        mock_app_valid_instance.run.return_value = json.dumps(data_valid)

        async def mock_async_add_executor_job(func, *args, **kwargs):
            return func(*args, **kwargs)

        with patch.object(
            hass,
            "async_add_executor_job",
            side_effect=mock_async_add_executor_job,
        ):
            coordinator_valid = HouseholdBinCoordinator(
                hass, mock_app_valid_instance, "Test Name", timeout=60
            )

            await coordinator_valid.async_refresh()

    # Verify that coordinator.data contains the expected processed data
    assert coordinator_valid.data == processed_data_valid

    sensor_valid = UKBinCollectionDataSensor(
        coordinator_valid, "Recycling", "test_recycling_available", {}
    )

    assert sensor_valid.available is True


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
            hass, mock_app_instance, "Test Name", timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

        assert coordinator.data == {}
        assert coordinator.last_update_success is True


def test_coordinator_custom_update_interval(hass, mock_config_entry):
    """Test that coordinator uses a custom update interval."""
    custom_interval = timedelta(hours=6)
    coordinator = HouseholdBinCoordinator(hass, MagicMock(), "Test Name", timeout=60)
    coordinator.update_interval = custom_interval

    assert coordinator.update_interval == custom_interval


@pytest.mark.asyncio
async def test_async_setup_entry_missing_required_fields(hass):
    """Test domain-level setup fails if 'name' is missing."""
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            # no "name"
            "council": "Test Council",
            "url": "https://example.com",
            "timeout": 60,
            "icon_color_mapping": {},
        },
        entry_id="test_missing_name",
    )

    with patch("custom_components.uk_bin_collection.UKBinCollectionApp") as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = "{}"
        hass.async_add_executor_job = AsyncMock(return_value="{}")

        with pytest.raises(ConfigEntryNotReady) as exc_info:
            # Call the domain-level function
            await async_setup_entry_domain(hass, mock_config_entry)

    assert "Missing 'name' in configuration." in str(exc_info.value)


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

        icon_color_mapping = {}

        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator,
        "General Waste",
        "test_general_waste_device_info",
        icon_color_mapping,
    )

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
        icon_color_mapping = {}

        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator, "Unknown Bin", "test_unknown_bin", icon_color_mapping
    )

    assert sensor.icon == "mdi:delete"
    assert sensor._color == "black"


def test_coordinator_update_interval(hass, mock_config_entry):
    """Test that coordinator uses the correct update interval."""
    coordinator = HouseholdBinCoordinator(hass, MagicMock(), "Test Name", timeout=60)
    assert coordinator.update_interval == timedelta(hours=12)


@pytest.mark.asyncio
async def test_manual_refresh_service(hass, mock_config_entry):
    """Test that calling manual_refresh logic triggers coordinator.async_request_refresh."""

    # 1) Manually set up the coordinator (just like your other sensor tests).
    hass.data = {}
    hass.data.setdefault(DOMAIN, {})

    # Create a coordinator
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps({"bins": []})

        hass.async_add_executor_job = AsyncMock(
            return_value=mock_app_instance.run.return_value
        )

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", timeout=60
        )
        await coordinator.async_config_entry_first_refresh()

    # Store coordinator in hass.data
    hass.data[DOMAIN][mock_config_entry.entry_id] = {"coordinator": coordinator}

    # 2) Duplicate the essence of handle_manual_refresh, but pass in a mock ServiceCall
    async def mock_handle_manual_refresh(call: ServiceCall):
        entry_id = call.data.get("entry_id")
        if not entry_id:
            return
        if entry_id not in hass.data[DOMAIN]:
            return
        c = hass.data[DOMAIN][entry_id].get("coordinator")
        if c:
            await c.async_request_refresh()

    # 3) Patch coordinator.async_request_refresh to confirm it gets called
    with patch.object(
        coordinator, "async_request_refresh", new_callable=AsyncMock
    ) as mock_refresh:
        # Construct a mock ServiceCall that includes the entry_id
        fake_call = ServiceCall(
            domain=DOMAIN,
            service="manual_refresh",
            data={"entry_id": mock_config_entry.entry_id},
        )
        await mock_handle_manual_refresh(fake_call)

        mock_refresh.assert_awaited_once()


def test_load_icon_color_mapping_invalid_json():
    from custom_components.uk_bin_collection.sensor import load_icon_color_mapping

    invalid_json = (
        '{"icon":"mdi:trash" "no_comma":true}'  # invalid JSON (missing comma)
    )
    with patch("logging.Logger.warning") as mock_warn:
        result = load_icon_color_mapping(invalid_json)
        # The function should return {}
        assert result == {}
        # Note the double space after the prefix – adjust to match the actual log message.
        mock_warn.assert_called_once_with(
            "[UKBinCollection] Invalid icon_color_mapping JSON: "
            f"{invalid_json}. Using default settings."
        )


@pytest.mark.asyncio
async def test_bin_sensor_missing_bin_type(hass, mock_config_entry):
    """Test that we log a warning and set state to Unknown when the bin type is missing."""
    # Suppose your coordinator’s data only has "Recycling"
    data = {"Recycling": datetime(2025, 2, 1).date()}
    # but the sensor is for "General Waste"

    # Create the coordinator
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.name = "Test Name"

    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", {}
    )

    with patch("logging.Logger.warning") as mock_warn:
        sensor.update_state()

    assert sensor.state == "Unknown"
    assert sensor.extra_state_attributes["days"] is None
    assert sensor.available is False
    mock_warn.assert_called_once_with(
        "[UKBinCollection] Data for bin type 'General Waste' is missing."
    )


@pytest.mark.asyncio
async def test_attribute_sensor_undefined_attribute_type(hass, mock_config_entry):
    coordinator = MagicMock()
    coordinator.data = {"Recycling": datetime(2025, 1, 1).date()}
    coordinator.name = "Test Coordinator"

    sensor = UKBinCollectionAttributeSensor(
        coordinator=coordinator,
        bin_type="Recycling",
        unique_id="test_recycling_undefined",
        attribute_type="Bogus Attribute",  # Will trigger the 'Undefined' path
        device_id="test_device",
        icon_color_mapping={},
    )

    with patch("logging.Logger.warning") as mock_warn:
        state = sensor.state
    assert state == "Undefined"
    mock_warn.assert_called_once_with(
        "[UKBinCollection] Undefined attribute type: Bogus Attribute"
    )


@pytest.mark.asyncio
async def test_bin_sensor_in_x_days(hass, freezer, mock_config_entry):
    freezer.move_to("2023-10-14")
    # next_collection is 5 days away
    future_date = dt_util.now().date() + timedelta(days=5)

    coordinator = MagicMock()
    coordinator.data = {"General Waste": future_date}
    coordinator.name = "Test Coordinator"

    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_gw_in_5_days", {}
    )
    assert sensor.state == "In 5 days"


def test_data_sensor_default_icon_unknown_type():
    coordinator = MagicMock()
    coordinator.data = {"Some Custom Bin": datetime(2025, 1, 1).date()}
    coordinator.name = "Test Name"

    sensor = UKBinCollectionDataSensor(coordinator, "Unknown Type", "test_unknown", {})
    assert sensor.icon == "mdi:delete"


def test_raw_json_sensor_partial_data():
    coordinator = MagicMock()
    # Only some bins have dates, e.g., "General Waste" is None
    coordinator.data = {"General Waste": None, "Recycling": datetime(2025, 1, 1).date()}
    coordinator.last_update_success = True
    sensor = UKBinCollectionRawJSONSensor(coordinator, "test_raw_json", "Test Name")

    state = sensor.state
    # Should JSON encode the 'None' bin
    assert state == '{"General Waste": null, "Recycling": "01/01/2025"}'


def test_data_sensor_unavailable_if_unknown_state():
    coordinator = MagicMock()
    coordinator.data = {}  # no bins
    coordinator.name = "Test Coordinator"

    sensor = UKBinCollectionDataSensor(coordinator, "General Waste", "test_gw", {})
    sensor.update_state()  # triggers "Unknown"
    assert sensor.available is False


def test_attribute_sensor_unavailable_if_coordinator_failed():
    coordinator = MagicMock()
    coordinator.data = {"Recycling": datetime(2025, 1, 1).date()}
    coordinator.last_update_success = False
    coordinator.name = "Test Coordinator"

    attr_sensor = UKBinCollectionAttributeSensor(
        coordinator, "Recycling", "test_attr_fail", "Colour", "device_id", {}
    )
    assert attr_sensor.available is False


import pytest
from unittest.mock import MagicMock
from datetime import datetime
from custom_components.uk_bin_collection.sensor import (
    create_sensor_entities,
    UKBinCollectionDataSensor,
    UKBinCollectionAttributeSensor,
    UKBinCollectionRawJSONSensor,
)


@pytest.mark.asyncio
def test_create_sensor_entities_coordinator_data():
    # Set up a coordinator with two bin types.
    coordinator = MagicMock()
    # For example, suppose today is 2025-02-08:
    coordinator.data = {
        "General Waste": date(2025, 2, 8),  # Today
        "Recycling": date(2025, 2, 9),  # Tomorrow
    }
    coordinator.name = "Test Coordinator"

    # Use a valid JSON mapping for General Waste only.
    icon_mapping_json = '{"General Waste":{"icon":"mdi:trash-can","color":"brown"}}'
    entities = create_sensor_entities(coordinator, "test_entry", icon_mapping_json)

    # We expect:
    #   2 main sensors (one per bin type),
    #   2 * 5 = 10 attribute sensors,
    #   1 raw JSON sensor,
    # Total 13 entities.
    assert len(entities) == 13

    # Check that for "General Waste", the icon from the mapping is used.
    gw_sensor = next(
        e
        for e in entities
        if isinstance(e, UKBinCollectionDataSensor) and "General Waste" in e.name
    )
    assert gw_sensor.icon == "mdi:trash-can"
    # And its attribute sensors (e.g., "Days Until Collection") can be tested:
    gw_attr_sensor = next(
        e
        for e in entities
        if isinstance(e, UKBinCollectionAttributeSensor)
        and "Days Until Collection" in e.name
    )
    # Trigger the state logic (which calls calculate_days_until)
    days_until = gw_attr_sensor.state
    # In our example, if today is 2025-02-08 and collection is today for General Waste,
    # days would be 0 (or if we adjust coordinator.data, you can compare against the expected value)
    # For this test we simply check that a value is returned (or you can be more specific if you set the dates)
    assert days_until is not None

    # Also, verify that a raw JSON sensor exists.
    raw_sensor = next(
        e for e in entities if isinstance(e, UKBinCollectionRawJSONSensor)
    )
    # Its state should be a JSON string containing keys for each bin type.
    raw_state = json.loads(raw_sensor.state)
    assert "General Waste" in raw_state and "Recycling" in raw_state


def test_create_sensor_entities_invalid_icon_json():
    coordinator = MagicMock()
    coordinator.data = {
        "General Waste": datetime(2025, 2, 10).date(),
    }
    coordinator.name = "Test Coordinator"

    invalid_json = '{"invalid":true,  '  # incomplete JSON
    with patch("logging.Logger.warning") as mock_warn:
        entities = create_sensor_entities(coordinator, "test_entry_id", invalid_json)

    # We still get 1 main sensor + 5 attribute sensors + 1 raw sensor => 7 total
    assert len(entities) == 7
    mock_warn.assert_called_once()
    # e.g. "... Invalid icon_color_mapping JSON: ... Using default settings."


@pytest.mark.asyncio
@freeze_time("2025-02-8")  # let's say "today" is 2025-02-8
def test_attribute_sensor_days_and_human_readable():
    coordinator = MagicMock()
    # Pretend "Food Waste" is 2 days away
    in_2_days = datetime(2025, 2, 10).date()
    coordinator.data = {"Food Waste": in_2_days}
    coordinator.name = "Coordinator Name"

    # Create sensors for that bin
    entities = create_sensor_entities(coordinator, "entry_id_days", "{}")
    # Find the attribute sensors for "Days Until Collection" & "Next Collection Human Readable"
    days_sensor = next(
        e
        for e in entities
        if isinstance(e, UKBinCollectionAttributeSensor)
        and "Days Until Collection" in e.name
    )
    human_sensor = next(
        e
        for e in entities
        if isinstance(e, UKBinCollectionAttributeSensor)
        and "Next Collection Human Readable" in e.name
    )

    # The .state property triggers the logic
    days_state = days_sensor.state
    human_state = human_sensor.state

    # If today is e.g. 2025-02-08, in_2_days is 2025-02-10 => that's 2 days away
    # "Days Until Collection" => 2
    # "Next Collection Human Readable" => "In 2 days" (assuming 2 != 1 => "days")
    assert days_state == 2
    assert human_state == "In 2 days"


def test_data_sensor_coordinator_update():
    coordinator = MagicMock()
    coordinator.data = {"General Waste": datetime(2025, 2, 10).date()}
    coordinator.name = "Coordinator Name"

    sensor = UKBinCollectionDataSensor(coordinator, "General Waste", "device_id", {})
    with patch.object(sensor, "update_state") as mock_update, patch.object(
        sensor, "async_write_ha_state"
    ) as mock_write:
        sensor._handle_coordinator_update()

    mock_update.assert_called_once()
    mock_write.assert_called_once()


@freeze_time("2025-02-10")  # let's say "today" is 2025-02-10
def test_data_sensor_today_tomorrow():
    coordinator = MagicMock()
    # Make 2 bins: one is "today" (2025-02-10), one is "tomorrow" (2025-02-11)
    coordinator.data = {
        "Waste Today": datetime(2025, 2, 10).date(),
        "Waste Tomorrow": datetime(2025, 2, 11).date(),
    }
    coordinator.name = "Coord"

    # create sensors
    entities = create_sensor_entities(coordinator, "entry_id", "{}")
    tdy_sensor = next(
        e
        for e in entities
        if isinstance(e, UKBinCollectionDataSensor) and "Waste Today" in e.name
    )
    tmw_sensor = next(
        e
        for e in entities
        if isinstance(e, UKBinCollectionDataSensor) and "Waste Tomorrow" in e.name
    )

    assert tdy_sensor.state == "Today"
    assert tmw_sensor.state == "Tomorrow"


@freeze_time("2025-02-08")
def test_create_sensor_entities_full_coverage(hass):
    coordinator = MagicMock()
    coordinator.data = {
        "General Waste": datetime(2025, 2, 8).date(),  # Today
        "Recycling": datetime(2025, 2, 9).date(),  # Tomorrow
        "Garden": datetime(2025, 2, 10).date(),  # 2 days
    }
    coordinator.name = "Full Coverage Coord"

    # Intentionally pass an invalid JSON to load_icon_color_mapping
    invalid_icon_json = '{"General Waste": {"icon":"mdi:trash-can"}, "broken"'
    with patch("logging.Logger.warning") as mock_warn:
        entities = create_sensor_entities(
            coordinator, "entry_id_abc", invalid_icon_json
        )

    # We get main sensors for 3 bins => 3
    # Each bin has 5 attribute sensors => 15
    # 1 raw sensor => 1
    # total => 19
    assert len(entities) == 19

    # Check the warning for invalid JSON was called
    mock_warn.assert_called_once()
    # e.g. "Invalid icon_color_mapping JSON: ... Using default settings."

    # Now pick an attribute sensor for "Days Until Collection" for "Garden"
    days_garden = next(e for e in entities if "Garden Days Until Collection" in e.name)
    # Trigger the state property => calls `calculate_days_until`
    days_val = days_garden.state
    assert days_val == 2  # Because 2025-02-10 is 2 days from 2025-02-08

    # Similarly, the raw JSON sensor
    raw_sensor = next(
        e for e in entities if isinstance(e, UKBinCollectionRawJSONSensor)
    )
    raw_state = raw_sensor.state
    # Should be a JSON with 3 keys, etc.
    # This triggers lines in raw-sensor code

    # Also test `_handle_coordinator_update` on the main sensor
    main_sensor = next(
        e
        for e in entities
        if "General Waste" in e.name and isinstance(e, UKBinCollectionDataSensor)
    )
    with patch.object(main_sensor, "update_state") as mock_up, patch.object(
        main_sensor, "async_write_ha_state"
    ) as mock_aw:
        main_sensor._handle_coordinator_update()
    mock_up.assert_called_once()
    mock_aw.assert_called_once()


###############################################################################
# Tests for UKBinCollectionAttributeSensor's state and helper methods
###############################################################################


def test_attribute_sensor_state_colour():
    """Test that if attribute type is 'Colour', state returns _color."""
    coordinator = MagicMock()
    # Provide some bin data though it isn’t used in this branch
    coordinator.data = {"Recycling": datetime(2025, 2, 10).date()}
    coordinator.name = "Test Coord"
    # Provide a mapping that supplies a color.
    icon_mapping = {"Recycling": {"icon": "mdi:recycle", "color": "green"}}
    sensor = UKBinCollectionAttributeSensor(
        coordinator, "Recycling", "uid1", "Colour", "dev1", icon_mapping
    )
    # The state for attribute "Colour" is simply the color.
    assert sensor.state == "green"


def test_attribute_sensor_state_bin_type():
    """Test that if attribute type is 'Bin Type', state returns the bin type."""
    coordinator = MagicMock()
    coordinator.data = {"Recycling": datetime(2025, 2, 10).date()}
    coordinator.name = "Test Coord"
    sensor = UKBinCollectionAttributeSensor(
        coordinator, "Recycling", "uid2", "Bin Type", "dev2", {}
    )
    assert sensor.state == "Recycling"


def test_attribute_sensor_state_next_collection_date_with_data():
    """Test that if attribute type is 'Next Collection Date' and data exists, state is the formatted date."""
    date_value = datetime(2025, 2, 10).date()
    coordinator = MagicMock()
    coordinator.data = {"Recycling": date_value}
    coordinator.name = "Test Coord"
    sensor = UKBinCollectionAttributeSensor(
        coordinator, "Recycling", "uid3", "Next Collection Date", "dev3", {}
    )
    expected = date_value.strftime("%d/%m/%Y")
    assert sensor.state == expected


def test_attribute_sensor_state_next_collection_date_no_data():
    """Test that if attribute type is 'Next Collection Date' and no data exists, state is 'Unknown'."""
    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.name = "Test Coord"
    sensor = UKBinCollectionAttributeSensor(
        coordinator, "Recycling", "uid4", "Next Collection Date", "dev4", {}
    )
    assert sensor.state == "Unknown"


@freeze_time("2025-02-08")
def test_attribute_sensor_state_next_collection_human_readable_today():
    """Test human‐readable state when bin collection is today."""
    coordinator = MagicMock()
    coordinator.data = {"Recycling": datetime(2025, 2, 8).date()}
    coordinator.name = "Test Coord"
    sensor = UKBinCollectionAttributeSensor(
        coordinator, "Recycling", "uid5", "Next Collection Human Readable", "dev5", {}
    )
    # When the collection date is today, expect "Today"
    assert sensor.state == "Today"


@freeze_time("2025-02-08")
def test_attribute_sensor_state_next_collection_human_readable_tomorrow():
    """Test human‐readable state when bin collection is tomorrow."""
    coordinator = MagicMock()
    coordinator.data = {"Recycling": datetime(2025, 2, 9).date()}
    coordinator.name = "Test Coord"
    sensor = UKBinCollectionAttributeSensor(
        coordinator, "Recycling", "uid6", "Next Collection Human Readable", "dev6", {}
    )
    assert sensor.state == "Tomorrow"


@freeze_time("2025-02-08")
def test_attribute_sensor_state_next_collection_human_readable_future():
    """Test human‐readable state when bin collection is more than one day away."""
    coordinator = MagicMock()
    coordinator.data = {"Recycling": datetime(2025, 2, 12).date()}  # 4 days later
    coordinator.name = "Test Coord"
    sensor = UKBinCollectionAttributeSensor(
        coordinator, "Recycling", "uid7", "Next Collection Human Readable", "dev7", {}
    )
    # 2025-02-12 is 4 days away from 2025-02-08
    assert sensor.state == "In 4 days"


@freeze_time("2025-02-08")
def test_attribute_sensor_state_days_until_collection_with_data():
    """Test that Days Until Collection returns the correct number of days."""
    coordinator = MagicMock()
    coordinator.data = {"Recycling": datetime(2025, 2, 11).date()}  # 3 days away
    coordinator.name = "Test Coord"
    sensor = UKBinCollectionAttributeSensor(
        coordinator, "Recycling", "uid8", "Days Until Collection", "dev8", {}
    )
    assert sensor.state == 3


@freeze_time("2025-02-08")
def test_attribute_sensor_state_days_until_collection_no_data():
    """Test that Days Until Collection returns -1 if no data is available."""
    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.name = "Test Coord"
    sensor = UKBinCollectionAttributeSensor(
        coordinator, "Recycling", "uid9", "Days Until Collection", "dev9", {}
    )
    assert sensor.state == -1


###############################################################################
# Tests for extra_state_attributes, device_info, and unique_id properties
###############################################################################


def test_data_sensor_extra_state_attributes():
    """Test that extra_state_attributes returns the correct dictionary."""
    coordinator = MagicMock()
    date_value = datetime(2025, 2, 10).date()
    coordinator.data = {"Recycling": date_value}
    coordinator.name = "Test Coord"
    sensor = UKBinCollectionDataSensor(coordinator, "Recycling", "uid10", {})
    expected_attributes = {
        STATE_ATTR_COLOUR: sensor.get_color(),  # without mapping, default is "black"
        STATE_ATTR_NEXT_COLLECTION: date_value.strftime("%d/%m/%Y"),
        STATE_ATTR_DAYS: (date_value - dt_util.now().date()).days,
    }
    assert sensor.extra_state_attributes == expected_attributes


def test_data_sensor_device_info_property():
    """Test that the device_info property returns the expected dictionary."""
    coordinator = MagicMock()
    coordinator.name = "Test Name"
    sensor = UKBinCollectionDataSensor(coordinator, "General Waste", "device123", {})
    expected = {
        "identifiers": {(DOMAIN, "device123")},
        "name": f"{coordinator.name} General Waste",
        "manufacturer": "UK Bin Collection",
        "model": "Bin Sensor",
        "sw_version": "1.0",
    }
    assert sensor.device_info == expected


def test_data_sensor_unique_id_property():
    """Test that unique_id property returns the correct value."""
    coordinator = MagicMock()
    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "unique_id_123", {}
    )
    assert sensor.unique_id == "unique_id_123"


###############################################################################
# Tests for create_sensor_entities() helper function
###############################################################################


def test_create_sensor_entities_coordinator_data():
    """Test that create_sensor_entities returns the correct sensor entities."""
    coordinator = MagicMock()
    # Suppose we have two bin types.
    coordinator.data = {
        "General Waste": date(2025, 2, 8),  # Today
        "Recycling": date(2025, 2, 9),  # Tomorrow
    }
    coordinator.name = "Test Coordinator"

    # Use a valid JSON mapping for General Waste only.
    icon_mapping_json = '{"General Waste":{"icon":"mdi:trash-can","color":"brown"}}'
    entities = create_sensor_entities(coordinator, "test_entry", icon_mapping_json)

    # Expect:
    #  2 main sensors (one for each bin type)
    #  2 * 5 = 10 attribute sensors (5 per bin type)
    #  1 raw JSON sensor
    # Total = 2 + 10 + 1 = 13
    assert len(entities) == 13

    # Verify that the General Waste sensor uses the icon mapping.
    gw_sensor = next(
        e
        for e in entities
        if isinstance(e, UKBinCollectionDataSensor) and "General Waste" in e.name
    )
    assert gw_sensor.icon == "mdi:trash-can"
    # Check that one of the attribute sensors exists (e.g. Days Until Collection)
    gw_attr = next(
        e
        for e in entities
        if isinstance(e, UKBinCollectionAttributeSensor)
        and "Days Until Collection" in e.name
    )
    assert gw_attr is not None

    # Verify that a raw JSON sensor is present.
    raw_sensor = next(
        e for e in entities if isinstance(e, UKBinCollectionRawJSONSensor)
    )
    raw_state = json.loads(raw_sensor.state)
    assert "General Waste" in raw_state and "Recycling" in raw_state


def test_create_sensor_entities_invalid_icon_json():
    """Test that create_sensor_entities logs a warning when icon_color_mapping is invalid."""
    coordinator = MagicMock()
    coordinator.data = {
        "General Waste": datetime(2025, 2, 10).date(),
    }
    coordinator.name = "Test Coordinator"

    invalid_json = '{"invalid":true,  '  # Incomplete JSON
    with patch("logging.Logger.warning") as mock_warn:
        entities = create_sensor_entities(coordinator, "test_entry_id", invalid_json)

    # With one bin type we expect: 1 main sensor + 5 attribute sensors + 1 raw sensor = 7 total
    assert len(entities) == 7
    mock_warn.assert_called_once()


###############################################################################
# Additional tests for the attribute sensor calculation methods
###############################################################################


@freeze_time("2025-02-08")
def test_attribute_sensor_days_and_human_readable():
    """Test that the attribute sensor returns correct human‐readable and days until collection."""
    coordinator = MagicMock()
    # Suppose "Food Waste" is 2 days away from 2025-02-08
    in_2_days = datetime(2025, 2, 10).date()
    coordinator.data = {"Food Waste": in_2_days}
    coordinator.name = "Coordinator Name"

    sensor = UKBinCollectionAttributeSensor(
        coordinator,
        "Food Waste",
        "uid_full",
        "Next Collection Human Readable",
        "dev_full",
        {},
    )
    # When there is data, the human-readable text should be "In 2 days"
    assert sensor.calculate_human_readable() == "In 2 days"
    # And calculate_days_until should return 2
    assert sensor.calculate_days_until() == 2


###############################################################################
# Tests for the Raw JSON Sensor behavior
###############################################################################


def test_raw_json_sensor_partial_data():
    """Test that the raw JSON sensor correctly encodes None values."""
    coordinator = MagicMock()
    # Only some bins have dates; for example, "General Waste" is None.
    coordinator.data = {"General Waste": None, "Recycling": datetime(2025, 1, 1).date()}
    coordinator.last_update_success = True
    sensor = UKBinCollectionRawJSONSensor(coordinator, "raw_uid", "Test Name")
    state = sensor.state
    # Expect that the None value is encoded as null in JSON.
    expected = '{"General Waste": null, "Recycling": "01/01/2025"}'
    assert state == expected


def test_data_sensor_unavailable_if_unknown_state():
    """Test that the sensor is marked unavailable when its state is 'Unknown'."""
    coordinator = MagicMock()
    coordinator.data = {}  # no bin data provided
    coordinator.name = "Test Coordinator"
    sensor = UKBinCollectionDataSensor(coordinator, "General Waste", "uid_unavail", {})
    sensor.update_state()  # This should set state to "Unknown"
    assert sensor.available is False


def test_attribute_sensor_unavailable_if_coordinator_failed():
    """Test that an attribute sensor is unavailable if the coordinator update failed."""
    coordinator = MagicMock()
    coordinator.data = {"Recycling": datetime(2025, 1, 1).date()}
    coordinator.last_update_success = False
    coordinator.name = "Test Coordinator"
    sensor = UKBinCollectionAttributeSensor(
        coordinator, "Recycling", "uid_fail", "Colour", "dev_fail", {}
    )
    assert sensor.available is False


# --- Additional tests for uncovered lines ---


def test_data_sensor_state_unknown_and_extra_attributes():
    """Test that if no bin data is provided the state is 'Unknown' and extra_state_attributes are set correctly."""
    # Create a coordinator with no data for the requested bin type.
    coordinator = MagicMock()
    coordinator.data = {}  # No data available.
    coordinator.name = "Test Coord"
    # Create a data sensor for a bin type that is not in the coordinator data.
    sensor = UKBinCollectionDataSensor(
        coordinator, "Nonexistent Bin", "device_unknown", {}
    )
    sensor.update_state()  # This should set the state to "Unknown"

    # Verify the state fallback
    assert sensor.state == "Unknown"

    # Verify extra_state_attributes returns default values:
    # The colour is determined by get_color()—with no mapping it returns "black"
    extra = sensor.extra_state_attributes
    assert extra[STATE_ATTR_COLOUR] == "black"
    # Since there is no bin date, the next collection attribute should be None.
    assert extra[STATE_ATTR_NEXT_COLLECTION] is None


def test_data_sensor_device_info_and_unique_id():
    """Test that the device_info and unique_id properties return the expected values."""
    coordinator = MagicMock()
    coordinator.name = "Test Coord"
    # Create a sensor with a given device ID.
    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "unique_id_test", {}
    )

    expected_device_info = {
        "identifiers": {(DOMAIN, "unique_id_test")},
        "name": f"{coordinator.name} General Waste",
        "manufacturer": "UK Bin Collection",
        "model": "Bin Sensor",
        "sw_version": "1.0",
    }
    # Test device_info property
    assert sensor.device_info == expected_device_info

    # Test unique_id property
    assert sensor.unique_id == "unique_id_test"


# --- Additional tests for the Attribute Sensor helper methods ---


@freeze_time("2025-02-08")
def test_attribute_sensor_calculate_human_readable_and_days_until():
    """Test the calculate_human_readable and calculate_days_until methods of the attribute sensor."""
    # Suppose "Food Waste" is 3 days away from 2025-02-08.
    future_date = datetime(2025, 2, 11).date()
    coordinator = MagicMock()
    coordinator.data = {"Food Waste": future_date}
    coordinator.name = "Test Coord"

    sensor = UKBinCollectionAttributeSensor(
        coordinator,
        "Food Waste",
        "attr_uid",
        "Next Collection Human Readable",
        "dev_uid",
        {},
    )
    # Manually call the helper methods:
    human_readable = sensor.calculate_human_readable()
    days_until = sensor.calculate_days_until()

    # From 2025-02-08 to 2025-02-11 is 3 days away.
    assert human_readable == "In 3 days"
    assert days_until == 3


# --- Additional tests for create_sensor_entities helper function ---


def test_create_sensor_entities_with_no_data():
    """Test create_sensor_entities returns sensors even when coordinator data is empty."""
    coordinator = MagicMock()
    coordinator.data = {}  # No bin types at all.
    coordinator.name = "Empty Coord"
    # Pass an empty JSON mapping.
    entities = create_sensor_entities(coordinator, "empty_entry", "{}")
    # We expect only the Raw JSON sensor to be created.
    # (since the for-loop over coordinator.data will not iterate if data is empty)
    assert len(entities) == 1
    assert isinstance(entities[0], UKBinCollectionRawJSONSensor)


# --- Additional tests for load_icon_color_mapping default return ---


def test_load_icon_color_mapping_empty_string():
    """Test that load_icon_color_mapping returns an empty dict if an empty string is provided."""
    result = load_icon_color_mapping("")
    assert result == {}


# (The test for invalid JSON is already present; see test_load_icon_color_mapping_invalid_json)

# --- Additional test for UKBinCollectionRawJSONSensor property behavior ---


def test_raw_json_sensor_with_no_data():
    """Test that the Raw JSON sensor returns '{}' when no coordinator data is available."""
    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.last_update_success = True
    sensor = UKBinCollectionRawJSONSensor(coordinator, "raw_test", "Test Name")
    assert sensor.state == "{}"
    # The extra_state_attributes should return an empty dict under the key "raw_data"
    assert sensor.extra_state_attributes == {"raw_data": {}}
    # Availability should depend on last_update_success
    assert sensor.available is True
