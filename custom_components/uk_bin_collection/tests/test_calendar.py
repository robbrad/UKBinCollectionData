# test_calendar.py

"""Unit tests for the UK Bin Collection Calendar platform."""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.calendar import CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.uk_bin_collection.calendar import (
    UKBinCollectionCalendar,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.uk_bin_collection.const import DOMAIN

from .common_utils import MockConfigEntry

pytest_plugins = ["freezegun"]

# Mock Data
MOCK_COORDINATOR_DATA = {
    "Recycling": date(2024, 4, 25),
    "General Waste": date(2024, 4, 26),
    "Garden Waste": date(2024, 4, 27),
}


@pytest.fixture
def mock_coordinator():
    """Fixture to create a mock DataUpdateCoordinator with sample data."""
    coordinator = MagicMock(spec=DataUpdateCoordinator)
    coordinator.data = MOCK_COORDINATOR_DATA.copy()
    coordinator.name = "Test Council"
    coordinator.last_update_success = True
    return coordinator


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
        entry_id="test_entry_id",
        unique_id="test_unique_id",
    )


@pytest.fixture
def hass_instance() -> HomeAssistant:
    """Return a fake HomeAssistant instance with a data attribute."""
    hass = MagicMock(spec=HomeAssistant)
    # Ensure hass.data is a dict and contains a dict for our DOMAIN
    hass.data = {DOMAIN: {}}
    return hass


# Tests


def test_calendar_entity_initialization(hass_instance, mock_coordinator):
    """Test that the calendar entity initializes correctly."""
    calendar = UKBinCollectionCalendar(
        coordinator=mock_coordinator,
        bin_type="Recycling",
        unique_id="test_entry_id_Recycling_calendar",
        name="Test Council Recycling Calendar",
    )

    assert calendar.name == "Test Council Recycling Calendar"
    assert calendar.unique_id == "test_entry_id_Recycling_calendar"
    assert calendar.device_info == {
        "identifiers": {(DOMAIN, "test_entry_id_Recycling_calendar")},
        "name": "Test Council Recycling Calendar Device",
        "manufacturer": "UK Bin Collection",
        "model": "Bin Collection Calendar",
        "sw_version": "1.0",
    }


def test_calendar_event_property(hass_instance, mock_coordinator):
    """Test that the event property returns the correct CalendarEvent."""
    collection_date = date(2024, 4, 25)
    mock_coordinator.data["Recycling"] = collection_date

    calendar = UKBinCollectionCalendar(
        coordinator=mock_coordinator,
        bin_type="Recycling",
        unique_id="test_entry_id_Recycling_calendar",
        name="Test Council Recycling Calendar",
    )

    expected_event = CalendarEvent(
        summary="Recycling Collection",
        start=collection_date,
        end=collection_date + timedelta(days=1),
        uid="test_entry_id_Recycling_calendar_2024-04-25",
    )

    assert calendar.event == expected_event


def test_calendar_event_property_no_data(hass_instance, mock_coordinator):
    """Test that the event property returns None when there's no collection date."""
    mock_coordinator.data["Recycling"] = None

    calendar = UKBinCollectionCalendar(
        coordinator=mock_coordinator,
        bin_type="Recycling",
        unique_id="test_entry_id_Recycling_calendar",
        name="Test Council Recycling Calendar",
    )

    assert calendar.event is None


@pytest.mark.asyncio
async def test_async_get_events(hass_instance, mock_coordinator):
    """Test that async_get_events returns correct events within the date range."""
    mock_coordinator.data = {
        "Recycling": date(2024, 4, 25),
        "General Waste": date(2024, 4, 26),
    }

    calendar = UKBinCollectionCalendar(
        coordinator=mock_coordinator,
        bin_type="Recycling",
        unique_id="test_entry_id_Recycling_calendar",
        name="Test Council Recycling Calendar",
    )

    start_date = datetime(2024, 4, 24)
    end_date = datetime(2024, 4, 26)

    expected_event = CalendarEvent(
        summary="Recycling Collection",
        start=date(2024, 4, 25),
        end=date(2024, 4, 26),
        uid="test_entry_id_Recycling_calendar_2024-04-25",
    )

    events = await calendar.async_get_events(hass_instance, start_date, end_date)
    assert events == [expected_event]


@pytest.mark.asyncio
async def test_async_get_events_no_events_in_range(hass_instance, mock_coordinator):
    """Test that async_get_events returns empty list when no events are in the range."""
    mock_coordinator.data = {
        "Recycling": date(2024, 4, 25),
    }

    calendar = UKBinCollectionCalendar(
        coordinator=mock_coordinator,
        bin_type="Recycling",
        unique_id="test_entry_id_Recycling_calendar",
        name="Test Council Recycling Calendar",
    )

    start_date = datetime(2024, 4, 26)
    end_date = datetime(2024, 4, 30)

    events = await calendar.async_get_events(hass_instance, start_date, end_date)
    assert events == []


def test_calendar_update_on_coordinator_change(hass_instance, mock_coordinator):
    """Test that the calendar entity updates when the coordinator's data changes."""
    collection_date_initial = date(2024, 4, 25)
    collection_date_updated = date(2024, 4, 26)
    mock_coordinator.data["Recycling"] = collection_date_initial

    calendar = UKBinCollectionCalendar(
        coordinator=mock_coordinator,
        bin_type="Recycling",
        unique_id="test_entry_id_Recycling_calendar",
        name="Test Council Recycling Calendar",
    )

    # Initially, the event should be for April 25
    expected_event_initial = CalendarEvent(
        summary="Recycling Collection",
        start=collection_date_initial,
        end=collection_date_initial + timedelta(days=1),
        uid="test_entry_id_Recycling_calendar_2024-04-25",
    )
    assert calendar.event == expected_event_initial

    # Update the coordinator's data
    mock_coordinator.data["Recycling"] = collection_date_updated
    mock_coordinator.async_write_ha_state = AsyncMock()

    # Simulate coordinator update by calling the update handler
    with patch.object(calendar, "async_write_ha_state", new=AsyncMock()) as mock_write:
        calendar._handle_coordinator_update()

    # The event should now be updated to April 26
    expected_event_updated = CalendarEvent(
        summary="Recycling Collection",
        start=collection_date_updated,
        end=collection_date_updated + timedelta(days=1),
        uid="test_entry_id_Recycling_calendar_2024-04-26",
    )
    assert calendar.event == expected_event_updated
    mock_write.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_creates_calendar_entities(
    hass_instance, mock_coordinator, mock_config_entry
):
    """Test that async_setup_entry creates calendar entities based on coordinator data."""
    # Mock the data in the coordinator
    mock_coordinator.data = {
        "Recycling": date(2024, 4, 25),
        "General Waste": date(2024, 4, 26),
    }

    # Patch the hass.data to include the coordinator
    hass_instance.data[DOMAIN][mock_config_entry.entry_id] = {
        "coordinator": mock_coordinator,
    }

    with patch(
        "custom_components.uk_bin_collection.calendar.UKBinCollectionCalendar",
        autospec=True,
    ) as mock_calendar_cls:
        mock_calendar_instance_recycling = MagicMock()
        mock_calendar_instance_general_waste = MagicMock()
        mock_calendar_cls.side_effect = [
            mock_calendar_instance_recycling,
            mock_calendar_instance_general_waste,
        ]

        await async_setup_entry(hass_instance, mock_config_entry, lambda entities: None)

        # Ensure that two calendar entities are created
        assert mock_calendar_cls.call_count == 2

        # Verify that the calendar entities are initialized with correct parameters
        mock_calendar_cls.assert_any_call(
            coordinator=mock_coordinator,
            bin_type="Recycling",
            unique_id="test_entry_id_Recycling_calendar",
            name="Test Council Recycling Calendar",
        )
        mock_calendar_cls.assert_any_call(
            coordinator=mock_coordinator,
            bin_type="General Waste",
            unique_id="test_entry_id_General Waste_calendar",
            name="Test Council General Waste Calendar",
        )


@pytest.mark.asyncio
async def test_async_setup_entry_handles_empty_data(hass_instance, mock_config_entry):
    """Test that async_setup_entry handles empty coordinator data gracefully."""
    # Mock an empty data coordinator
    mock_coordinator = MagicMock(spec=DataUpdateCoordinator)
    mock_coordinator.data = {}
    mock_coordinator.name = "Test Council"
    mock_coordinator.last_update_success = True

    # Patch the hass.data to include the coordinator
    hass_instance.data[DOMAIN][mock_config_entry.entry_id] = {
        "coordinator": mock_coordinator,
    }

    with patch(
        "custom_components.uk_bin_collection.calendar.UKBinCollectionCalendar",
        autospec=True,
    ) as mock_calendar_cls:
        await async_setup_entry(hass_instance, mock_config_entry, lambda entities: None)

        # No calendar entities should be created since there's no data
        mock_calendar_cls.assert_not_called()


@pytest.mark.asyncio
async def test_async_setup_entry_handles_coordinator_failure(
    hass_instance, mock_config_entry
):
    """Test that async_setup_entry raises ConfigEntryNotReady on coordinator failure."""
    mock_coordinator = MagicMock(spec=DataUpdateCoordinator)
    mock_coordinator.async_config_entry_first_refresh.side_effect = Exception(
        "Update failed"
    )
    mock_coordinator.name = "Test Council"

    # Patch the hass.data to include the coordinator
    hass_instance.data[DOMAIN][mock_config_entry.entry_id] = {
        "coordinator": mock_coordinator,
    }

    with pytest.raises(Exception, match="Update failed"):
        await async_setup_entry(hass_instance, mock_config_entry, lambda entities: None)


@pytest.mark.asyncio
async def test_async_unload_entry(hass_instance, mock_coordinator, mock_config_entry):
    """Test that async_unload_entry unloads calendar entities correctly."""
    # Prepare the coordinator data
    mock_coordinator.data = {"Recycling": date(2024, 4, 25)}
    mock_coordinator.name = "Test Council"
    hass_instance.data[DOMAIN][mock_config_entry.entry_id] = {
        "coordinator": mock_coordinator
    }

    result = await async_unload_entry(hass_instance, mock_config_entry, None)
    assert result is True


def test_calendar_entity_available_property(hass_instance, mock_coordinator):
    """Test the available property of the calendar entity."""
    # When data is present and last_update_success is True
    mock_coordinator.last_update_success = True
    mock_coordinator.data["Recycling"] = date(2024, 4, 25)

    calendar = UKBinCollectionCalendar(
        coordinator=mock_coordinator,
        bin_type="Recycling",
        unique_id="test_entry_id_Recycling_calendar",
        name="Test Council Recycling Calendar",
    )

    assert calendar.available is True

    # When data is missing
    mock_coordinator.data["Recycling"] = None
    assert calendar.available is False

    # When last_update_success is False
    mock_coordinator.last_update_success = False
    calendar._state = "Unknown"  # Assuming state is set to "Unknown" when unavailable
    assert calendar.available is False


@pytest.mark.asyncio
async def test_async_setup_entry_creates_no_calendar_entities_on_empty_data(
    hass_instance, mock_config_entry
):
    """Test that async_setup_entry does not create calendar entities when coordinator data is empty."""
    mock_coordinator = MagicMock(spec=DataUpdateCoordinator)
    mock_coordinator.data = {}
    mock_coordinator.name = "Test Council"
    mock_coordinator.last_update_success = True

    # Patch the hass.data to include the coordinator
    hass_instance.data[DOMAIN][mock_config_entry.entry_id] = {
        "coordinator": mock_coordinator,
    }

    with patch(
        "custom_components.uk_bin_collection.calendar.UKBinCollectionCalendar",
        autospec=True,
    ) as mock_calendar_cls:
        await async_setup_entry(hass_instance, mock_config_entry, lambda entities: None)

        # No calendar entities should be created
        mock_calendar_cls.assert_not_called()


@pytest.mark.asyncio
async def test_async_get_events_multiple_events_same_day(
    hass_instance, mock_coordinator
):
    """Test async_get_events when multiple bin types have the same collection date."""
    mock_coordinator.data = {
        "Recycling": date(2024, 4, 25),
        "General Waste": date(2024, 4, 25),
    }

    calendar_recycling = UKBinCollectionCalendar(
        coordinator=mock_coordinator,
        bin_type="Recycling",
        unique_id="test_entry_id_Recycling_calendar",
        name="Test Council Recycling Calendar",
    )

    calendar_general_waste = UKBinCollectionCalendar(
        coordinator=mock_coordinator,
        bin_type="General Waste",
        unique_id="test_entry_id_General Waste_calendar",
        name="Test Council General Waste Calendar",
    )

    start_date = datetime(2024, 4, 24)
    end_date = datetime(2024, 4, 26)

    expected_event_recycling = CalendarEvent(
        summary="Recycling Collection",
        start=date(2024, 4, 25),
        end=date(2024, 4, 26),
        uid="test_entry_id_Recycling_calendar_2024-04-25",
    )

    expected_event_general_waste = CalendarEvent(
        summary="General Waste Collection",
        start=date(2024, 4, 25),
        end=date(2024, 4, 26),
        uid="test_entry_id_General Waste_calendar_2024-04-25",
    )

    events_recycling = await calendar_recycling.async_get_events(
        hass_instance, start_date, end_date
    )
    events_general_waste = await calendar_general_waste.async_get_events(
        hass_instance, start_date, end_date
    )

    assert events_recycling == [expected_event_recycling]
    assert events_general_waste == [expected_event_general_waste]


@pytest.mark.asyncio
async def test_async_get_events_no_coordinator_data(hass_instance, mock_coordinator):
    """Test async_get_events when coordinator has no data."""
    mock_coordinator.data = {}
    calendar = UKBinCollectionCalendar(
        coordinator=mock_coordinator,
        bin_type="Recycling",
        unique_id="test_entry_id_Recycling_calendar",
        name="Test Council Recycling Calendar",
    )

    start_date = datetime(2024, 4, 24)
    end_date = datetime(2024, 4, 26)

    events = await calendar.async_get_events(hass_instance, start_date, end_date)
    assert events == []


def test_calendar_entity_available_property_no_data(hass_instance, mock_coordinator):
    """Test that the calendar's available property is False when there's no data."""
    mock_coordinator.data["Recycling"] = None

    calendar = UKBinCollectionCalendar(
        coordinator=mock_coordinator,
        bin_type="Recycling",
        unique_id="test_entry_id_Recycling_calendar",
        name="Test Council Recycling Calendar",
    )

    assert calendar.available is False


@pytest.mark.asyncio
async def test_calendar_entity_extra_state_attributes(hass_instance, mock_coordinator):
    """Test the extra_state_attributes property of the calendar entity."""
    mock_coordinator.data["Recycling"] = date(2024, 4, 25)

    calendar = UKBinCollectionCalendar(
        coordinator=mock_coordinator,
        bin_type="Recycling",
        unique_id="test_entry_id_Recycling_calendar",
        name="Test Council Recycling Calendar",
    )

    # Check the extra_state_attributes, assuming it returns an empty dict
    assert calendar.extra_state_attributes == {}


@pytest.mark.asyncio
async def test_async_setup_entry_handles_coordinator_partial_data(
    hass_instance, mock_config_entry
):
    """Test that async_setup_entry creates calendar entities only for available data."""
    mock_coordinator = MagicMock(spec=DataUpdateCoordinator)
    mock_coordinator.data = {
        "Recycling": date(2024, 4, 25),
        "General Waste": None,  # No collection date
        "Garden Waste": date(2024, 4, 27),
    }
    mock_coordinator.name = "Test Council"
    mock_coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)

    hass_instance.data[DOMAIN][mock_config_entry.entry_id] = {
        "coordinator": mock_coordinator
    }

    with patch(
        "custom_components.uk_bin_collection.calendar.UKBinCollectionCalendar",
        autospec=True,
    ) as mock_calendar_cls:
        mock_calendar_instance_recycling = MagicMock()
        mock_calendar_instance_garden_waste = MagicMock()
        mock_calendar_cls.side_effect = [
            mock_calendar_instance_recycling,
            mock_calendar_instance_garden_waste,
        ]

        await async_setup_entry(hass_instance, mock_config_entry, lambda entities: None)

        # Ensure that two calendar entities are created (skipping "General Waste")
        assert mock_calendar_cls.call_count == 2

        # Verify that the calendar entities are initialized with correct parameters
        mock_calendar_cls.assert_any_call(
            coordinator=mock_coordinator,
            bin_type="Recycling",
            unique_id="{}_{bin}_calendar".format(
                mock_config_entry.entry_id, bin="Recycling"
            ),
            name="Test Council Recycling Calendar",
        )
        mock_calendar_cls.assert_any_call(
            coordinator=mock_coordinator,
            bin_type="Garden Waste",
            unique_id="{}_{bin}_calendar".format(
                mock_config_entry.entry_id, bin="Garden Waste"
            ),
            name="Test Council Garden Waste Calendar",
        )
