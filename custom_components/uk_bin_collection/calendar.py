"""Calendar platform support for UK Bin Collection Data."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN, LOG_PREFIX

_LOGGER = logging.getLogger(__name__)


class UKBinCollectionCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar entity for UK Bin Collection Data."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        bin_type: str,
        unique_id: str,
        name: str,
    ) -> None:
        """Initialize the calendar entity."""
        super().__init__(coordinator)
        self._bin_type = bin_type
        self._unique_id = unique_id
        self._name = name
        self._attr_unique_id = unique_id

        # Optionally, set device_info if you have device grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, unique_id)},
            "name": f"{self._name} Device",
            "manufacturer": "UK Bin Collection",
            "model": "Bin Collection Calendar",
            "sw_version": "1.0",
        }

    @property
    def name(self) -> str:
        """Return the name of the calendar."""
        return self._name

    @property
    def event(self) -> Optional[CalendarEvent]:
        """Return the next collection event."""
        collection_date = self.coordinator.data.get(self._bin_type)
        if not collection_date:
            _LOGGER.debug(f"{LOG_PREFIX} No collection date available for '{self._bin_type}'.")
            return None

        return self._create_calendar_event(collection_date)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> List[CalendarEvent]:
        """Return all events within a specific time frame."""
        events: List[CalendarEvent] = []
        collection_date = self.coordinator.data.get(self._bin_type)

        if not collection_date:
            return events

        # The test expects comparison between date parts.
        if start_date.date() <= collection_date <= end_date.date():
            events.append(self._create_calendar_event(collection_date))

        return events

    def _create_calendar_event(self, collection_date: datetime.date) -> CalendarEvent:
        """Create a CalendarEvent for a given collection date."""
        return CalendarEvent(
            summary=f"{self._bin_type} Collection",
            start=collection_date,
            end=collection_date + timedelta(days=1),
            uid=f"{self.unique_id}_{collection_date.isoformat()}",
        )

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the calendar."""
        return self._unique_id

    @property
    def available(self) -> bool:
        """Return if entity is available.

        The entity is considered available if the coordinator’s last update was successful
        and we have a valid collection date for the bin type.
        """
        return self.coordinator.last_update_success and (self.coordinator.data.get(self._bin_type) is not None)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updates from the coordinator and refresh calendar state."""
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UK Bin Collection Calendar from a config entry."""
    _LOGGER.info(f"{LOG_PREFIX} Setting up UK Bin Collection Calendar platform.")

    # Retrieve the coordinator from hass.data
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    # Wait for the first refresh. This will raise if the update fails.
    await coordinator.async_config_entry_first_refresh()

    # Create calendar entities only for bin types that have a valid date
    entities = []
    for bin_type, collection_date in coordinator.data.items():
        if collection_date is None:
            continue
        unique_id = calc_unique_calendar_id(config_entry.entry_id, bin_type)
        name = f"{coordinator.name} {bin_type} Calendar"
        entities.append(
            UKBinCollectionCalendar(
                coordinator=coordinator,
                bin_type=bin_type,
                unique_id=unique_id,
                name=name,
            )
        )

    # Register all calendar entities with Home Assistant
    async_add_entities(entities)
    _LOGGER.debug(f"{LOG_PREFIX} Calendar entities added: {[entity.name for entity in entities]}")


async def async_unload_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_remove_entities: Any,
) -> bool:
    """Unload a config entry."""
    # Unloading is handled in init.py
    return True


def calc_unique_calendar_id(entry_id: str, bin_type: str) -> str:
    """Calculate a unique ID for the calendar."""
    return f"{entry_id}_{bin_type}_calendar"
