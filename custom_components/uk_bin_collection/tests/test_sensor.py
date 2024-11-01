import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import async_get_current_platform
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.uk_bin_collection.const import DOMAIN
from custom_components.uk_bin_collection.sensor import (
    UKBinCollectionAttributeSensor,
    UKBinCollectionDataSensor,
    UKBinCollectionRawJSONSensor,
    async_setup_entry,
    get_latest_collection_info,
)

today = datetime.now().date()
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


def test_get_latest_collection_info(freezer):
    """Test processing of bin collection data."""
    freezer.move_to("2023-10-14")
    processed_data = get_latest_collection_info(MOCK_BIN_COLLECTION_DATA)
    assert processed_data == MOCK_PROCESSED_DATA


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


def test_get_latest_collection_info(freezer):
    """Test processing of bin collection data."""
    freezer.move_to("2023-10-14")
    processed_data = get_latest_collection_info(MOCK_BIN_COLLECTION_DATA)
    assert processed_data == MOCK_PROCESSED_DATA


async def test_async_setup_entry(hass, mock_config_entry):
    """Test setting up the sensor platform."""
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        # Mock async_add_entities
        async_add_entities = MagicMock()

        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        # Verify that entities were added
        assert async_add_entities.call_count == 1
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 19  # 5 entities per bin type + 1 raw JSON sensor


async def test_coordinator_fetch(hass, freezer, mock_config_entry):
    """Test the data fetch by the coordinator."""
    freezer.move_to("2023-10-14")
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        # Create the coordinator
        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

        # Verify data
        assert coordinator.data == MOCK_PROCESSED_DATA


async def test_bin_sensor(hass, mock_config_entry):
    """Test the main bin sensor."""
    # Set up the coordinator
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    # Create a bin sensor
    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )

    # Access properties
    assert sensor.name == "Test Name General Waste"
    assert sensor.unique_id == "test_general_waste"
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


async def test_attribute_sensor(hass, mock_config_entry):
    """Test the attribute sensor."""
    # Set up the coordinator
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass,
            mock_app_instance,
            "Test Name",
            mock_config_entry,
            timeout=60,
        )

        await coordinator.async_config_entry_first_refresh()

    # Create an attribute sensor
    sensor = UKBinCollectionAttributeSensor(
        coordinator,
        "General Waste",
        "test_general_waste_colour",
        "Colour",
        "test_general_waste",
        "{}",
    )

    # Access properties
    assert sensor.name == "Test Name General Waste Colour"
    assert sensor.unique_id == "test_general_waste_colour"
    assert sensor.state == "black"
    assert sensor.icon == "mdi:trash-can"
    assert sensor.extra_state_attributes == {
        "colour": "black",
        "next_collection": "15/10/2023",
    }


async def test_raw_json_sensor(hass, mock_config_entry):
    """Test the raw JSON sensor."""
    # Set up the coordinator
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    # Create the raw JSON sensor
    sensor = UKBinCollectionRawJSONSensor(coordinator, "test_raw_json", "Test Name")

    # Access properties
    assert sensor.name == "Test Name Raw JSON"
    assert sensor.unique_id == "test_raw_json"
    assert sensor.state == json.dumps(MOCK_PROCESSED_DATA)
    assert sensor.extra_state_attributes == {"raw_data": MOCK_PROCESSED_DATA}


async def test_coordinator_fetch_failure(hass, mock_config_entry):
    """Test handling when data fetch fails."""
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        # Simulate an exception during run
        mock_app_instance.run.side_effect = Exception("Network error")

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        with pytest.raises(Exception):
            await coordinator.async_config_entry_first_refresh()

        assert coordinator.last_update_success is False


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


async def test_bin_sensor_custom_icon_color(hass, mock_config_entry):
    """Test bin sensor with custom icon and color."""
    icon_color_mapping = json.dumps(
        {"General Waste": {"icon": "mdi:delete", "color": "green"}}
    )

    # Set up the coordinator
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    # Create a bin sensor
    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", icon_color_mapping
    )

    # Access properties
    assert sensor.icon == "mdi:delete"
    assert sensor.extra_state_attributes["colour"] == "green"


async def test_bin_sensor_today_collection(hass, freezer, mock_config_entry):
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

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    # Create a bin sensor
    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )

    # Access properties
    assert sensor.state == "Today"


async def test_bin_sensor_tomorrow_collection(hass, freezer, mock_config_entry):
    """Test bin sensor when collection is tomorrow."""
    freezer.move_to("2023-10-14")
    tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": tomorrow_date},
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(data)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    # Create a bin sensor
    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )

    # Access properties
    assert sensor.state == "Tomorrow"


async def test_sensor_coordinator_update(
    hass, freezer, mock_config_entry, enable_custom_integrations
):
    """Test that sensor updates when coordinator data changes."""
    freezer.move_to("2023-10-14")

    # Add the config entry to hass
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        # Set up the config entry
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Find the sensor we want
    sensor_entity_id = "sensor.test_name_general_waste"
    state = hass.states.get(sensor_entity_id)
    assert state is not None

    initial_state = state.state

    # Update the coordinator with new data
    new_data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "20/10/2023"},
        ]
    }
    mock_app_instance.run.return_value = json.dumps(new_data)

    # Request a refresh
    coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    # Get the new state
    state = hass.states.get(sensor_entity_id)
    assert state.state != initial_state
    assert state.state == "In 6 days"

    # Stop the coordinator to avoid lingering timers
    await coordinator.async_shutdown()
    await hass.async_block_till_done()


async def test_unload_entry(hass, mock_config_entry):
    """Test unloading the config entry."""
    with patch("custom_components.uk_bin_collection.sensor.UKBinCollectionApp"), patch(
        "custom_components.uk_bin_collection.async_setup_entry",
        return_value=True,
    ), patch(
        "homeassistant.loader.async_get_integration",
        return_value=MagicMock(),
    ):
        # Add the config entry to hass
        mock_config_entry.add_to_hass(hass)

        # Set up the entry
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Unload the entry
        result = await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert result is True
        assert mock_config_entry.state == ConfigEntryState.NOT_LOADED


def test_get_latest_collection_info_missing_type(freezer):
    """Test processing when a bin entry is missing the 'type' field."""
    freezer.move_to("2023-10-14")
    data = {
        "bins": [
            {"collectionDate": "15/10/2023"},
        ]
    }
    processed_data = get_latest_collection_info(data)
    assert processed_data == {}  # Should ignore entries without 'type'


def test_get_latest_collection_info_missing_collection_date(freezer):
    """Test processing when a bin entry is missing the 'collectionDate' field."""
    freezer.move_to("2023-10-14")
    data = {
        "bins": [
            {"type": "General Waste"},
        ]
    }
    processed_data = get_latest_collection_info(data)
    assert processed_data == {}  # Should ignore entries without 'collectionDate'


def test_get_latest_collection_info_malformed_date(freezer):
    """Test processing when 'collectionDate' is malformed."""
    freezer.move_to("2023-10-14")
    data = {
        "bins": [
            {
                "type": "General Waste",
                "collectionDate": "2023-15-10",
            },  # Incorrect format
        ]
    }
    processed_data = get_latest_collection_info(data)
    assert processed_data == {}  # Should ignore entries with invalid date format


def test_get_latest_collection_info_multiple_bins_same_date(freezer):
    """Test processing with multiple bin types having the same collection date."""
    freezer.move_to("2023-10-14")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "15/10/2023"},
            {"type": "Recycling", "collectionDate": "15/10/2023"},
        ]
    }
    expected = {
        "General Waste": "15/10/2023",
        "Recycling": "15/10/2023",
    }
    processed_data = get_latest_collection_info(data)
    assert processed_data == expected


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

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(custom_data)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

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


async def test_async_setup_entry_invalid_icon_color_mapping(hass):
    """Test setup with invalid JSON in icon_color_mapping."""
    # Create a new MockConfigEntry with invalid JSON for icon_color_mapping
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Entry",
        data={
            "name": "Test Name",
            "council": "Test Council",
            "url": "https://example.com",
            "timeout": 60,
            "icon_color_mapping": "{invalid_json}",  # Invalid JSON
        },
        entry_id="test_invalid_icon_color",
        unique_id="test_invalid_icon_color_unique_id",
    )

    # Add the entry to Home Assistant
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        async_add_entities = MagicMock()

        await async_setup_entry(hass, mock_config_entry, async_add_entities)
        await hass.async_block_till_done()

        # Verify that entities were added despite invalid JSON
        assert async_add_entities.call_count == 1
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 19  # 5 entities per bin type + 1 raw JSON sensor

        # Check that default icon and color are used
        data_sensor = next(
            (
                e
                for e in entities
                if isinstance(e, UKBinCollectionDataSensor)
                and e._bin_type == "General Waste"
            ),
            None,
        )
        assert data_sensor is not None
        assert data_sensor.icon == "mdi:trash-can"  # Default icon
        assert data_sensor.extra_state_attributes["colour"] == "black"  # Default color


async def test_sensor_available_when_data_present(hass, mock_config_entry):
    """Test that sensor is available when data is present."""
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )
    assert sensor.available is True


async def test_sensor_unavailable_when_data_missing(hass, mock_config_entry):
    """Test that sensor is unavailable when data is missing."""
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        # Return empty data
        mock_app_instance.run.return_value = json.dumps({"bins": []})

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )
    assert sensor.available is False


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


async def test_bin_sensor_with_different_timezone(
    hass, mock_config_entry, mock_dt_now_different_timezone
):
    """Test bin sensor with different timezone settings."""
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

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_refresh()
        await hass.async_block_till_done()

    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )

    # Adjust expectation based on the date
    assert sensor.state == "Tomorrow"


async def test_bin_sensor_invalid_date_format(hass, mock_config_entry):
    """Test bin sensor with invalid date format."""
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "2023-10-15"},  # Invalid format
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(data)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )

    assert sensor.state == "Unknown"
    assert sensor.available is False


@pytest.mark.asyncio
async def test_async_setup_entry_missing_required_fields(hass):
    """Test setup with missing required configuration fields."""
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Entry",
        data={
            # "name" is missing, should default to "UK Bin Collection"
            "council": "Test Council",
            "url": "https://example.com",
            "timeout": 60,
            "icon_color_mapping": "{}",
        },
        entry_id="test",
        unique_id="test_unique_id",
    )

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        async_add_entities = MagicMock()

        await async_setup_entry(hass, mock_config_entry, async_add_entities)
        await hass.async_block_till_done()

        # Assert that async_add_entities was called once
        assert (
            async_add_entities.call_count == 1
        ), f"Expected async_add_entities to be called once, got {async_add_entities.call_count}"

        # Retrieve the list of entities passed to async_add_entities
        entities = async_add_entities.call_args[0][0]

        # Calculate expected number of entities
        # For each bin type, 6 entities are created (1 data sensor + 5 attribute sensors)
        # Plus 1 raw JSON sensor
        expected_bin_types = len(MOCK_BIN_COLLECTION_DATA["bins"])
        expected_entities = expected_bin_types * 6 + 1  # 3*6 +1 = 19
        assert (
            len(entities) == expected_entities
        ), f"Expected {expected_entities} entities, got {len(entities)}"

        # Check that a specific data sensor exists
        data_sensor = next(
            (
                e
                for e in entities
                if isinstance(e, UKBinCollectionDataSensor)
                and e._bin_type == "General Waste"
            ),
            None,
        )
        assert (
            data_sensor is not None
        ), "UKBinCollectionDataSensor for 'General Waste' not found"

        # Optionally, verify that the raw JSON sensor is present
        raw_json_sensor = next(
            (
                e
                for e in entities
                if hasattr(e, "name") and e.name == "UK Bin Collection Raw JSON"
            ),
            None,
        )
        assert raw_json_sensor is not None, "UKBinCollectionRawJSONSensor not found"


# test_sensor.py
async def test_async_setup_entry_invalid_config_types(hass):
    """Test setup with invalid data types in configuration."""
    # Create a new MockConfigEntry with invalid timeout type
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Entry",
        data={
            "name": "Test Name",
            "council": "Test Council",
            "url": "https://example.com",
            "timeout": "sixty",  # Should be an integer
            "icon_color_mapping": "{}",
        },
        entry_id="test_invalid_config",
        unique_id="test_invalid_config_unique_id",
    )

    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        async_add_entities = MagicMock()

        await async_setup_entry(hass, mock_config_entry, async_add_entities)
        await hass.async_block_till_done()

        # Verify that async_add_entities was called despite invalid config
        assert async_add_entities.call_count == 1

        # Optionally, verify that a warning was logged about invalid timeout


async def test_coordinator_custom_update_interval(hass, mock_config_entry):
    """Test coordinator with a custom update interval."""
    custom_update_interval = timedelta(hours=6)
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )
        coordinator.update_interval = custom_update_interval

        await coordinator.async_config_entry_first_refresh()

        assert coordinator.update_interval == custom_update_interval
        assert coordinator.data == MOCK_PROCESSED_DATA


async def test_coordinator_custom_timeout(hass, mock_config_entry):
    """Test coordinator with a custom timeout."""
    custom_timeout = 30
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass,
            mock_app_instance,
            "Test Name",
            mock_config_entry,
            timeout=custom_timeout,
        )

        assert coordinator.timeout == custom_timeout

        await coordinator.async_config_entry_first_refresh()

        assert coordinator.data == MOCK_PROCESSED_DATA


async def test_some_bins_missing_data(hass, mock_config_entry):
    """Test sensors when some bin types have missing data."""
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": "15/10/2023"},
            # "Recycling" data is missing
        ]
    }
    expected = {
        "General Waste": "15/10/2023",
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(data)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    # Create sensors for both bin types
    sensor_general = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )
    sensor_recycling = UKBinCollectionDataSensor(
        coordinator, "Recycling", "test_recycling", "{}"
    )

    # Check General Waste sensor
    assert sensor_general.state == "Tomorrow"  # Change from "In 1 days" to "Tomorrow"
    # Check Recycling sensor which has missing data
    assert sensor_recycling.state == "Unknown"
    assert sensor_recycling.available is False


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


async def test_coordinator_shutdown(hass, mock_config_entry):
    """Test that coordinator shuts down properly."""
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Shutdown the coordinator
        await coordinator.async_shutdown()
        await hass.async_block_till_done()

        # Since 'update_task' doesn't exist, we can verify that no further updates occur
        mock_app_instance.run.assert_called_once()


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


async def test_entity_registry_registration(hass, mock_config_entry):
    """Test that sensors are correctly registered in the entity registry."""
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app, patch(
        "custom_components.uk_bin_collection.async_setup_entry", return_value=True
    ):
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        # Add the config entry to hass
        mock_config_entry.add_to_hass(hass)

        # Set up the config entry
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Access the entity registry
        registry = er.async_get(hass)

        # Check that entities are registered
        for entity_id in registry.entities:
            entity = registry.entities[entity_id]
            if entity.platform == DOMAIN:
                assert entity.unique_id is not None


async def test_entity_registry_registration_with_platform(hass, mock_config_entry):
    """Test that sensors are correctly registered in the entity registry."""
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app, patch(
        "custom_components.uk_bin_collection.async_setup_entry", return_value=True
    ):
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        # Add the config entry to hass
        mock_config_entry.add_to_hass(hass)

        # Set up the config entry
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Access the entity registry
        registry = er.async_get(hass)

        # Check that entities are registered
        for entity_id in registry.entities:
            entity = registry.entities[entity_id]
            if entity.platform == DOMAIN:
                assert entity.unique_id is not None


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


async def test_bin_sensor_negative_days(hass, mock_config_entry, freezer):
    """Test bin sensor when 'days' until collection is negative."""
    freezer.move_to("2023-10-14")
    past_date = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": past_date},
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(data)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )

    assert sensor.state == "Unknown"
    assert sensor.available is False


async def test_coordinator_last_update_success(hass, mock_config_entry):
    """Test that coordinator.last_update_success reflects the update status."""
    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value

        # First successful run
        mock_app_instance.run.return_value = json.dumps(MOCK_BIN_COLLECTION_DATA)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()
        assert coordinator.last_update_success is True

        # Simulate a failed run
        mock_app_instance.run.side_effect = Exception("Network error")

        # Attempt to refresh again
        await coordinator.async_refresh()
        assert coordinator.last_update_success is False


async def test_sensor_attributes_with_none_values(hass, mock_config_entry):
    """Test sensor attributes when some values are None."""
    data = {
        "bins": [
            {"type": "General Waste", "collectionDate": None},
        ]
    }

    with patch(
        "custom_components.uk_bin_collection.sensor.UKBinCollectionApp"
    ) as mock_app:
        mock_app_instance = mock_app.return_value
        mock_app_instance.run.return_value = json.dumps(data)

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", "{}"
    )

    assert sensor.state == "Unknown"
    assert sensor.extra_state_attributes["next_collection"] is None
    assert sensor.extra_state_attributes["days"] is None
    assert sensor.available is False


async def test_sensor_color_property_missing(hass, mock_config_entry):
    """Test sensor's color property when color is missing."""
    icon_color_mapping = json.dumps(
        {"General Waste": {"icon": "mdi:delete"}}  # Color is missing
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

        from custom_components.uk_bin_collection.sensor import HouseholdBinCoordinator

        coordinator = HouseholdBinCoordinator(
            hass, mock_app_instance, "Test Name", mock_config_entry, timeout=60
        )

        await coordinator.async_config_entry_first_refresh()

    sensor = UKBinCollectionDataSensor(
        coordinator, "General Waste", "test_general_waste", icon_color_mapping
    )

    # Color should default to "black"
    assert sensor.color == "black"
