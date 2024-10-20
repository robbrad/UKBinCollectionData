"""Support for UK Bin Collection Dat sensors."""

from datetime import timedelta, datetime
from dateutil import parser
import async_timeout
import json


from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_time_interval

from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
import homeassistant.util.dt as dt_util
from .const import (
    DOMAIN,
    LOG_PREFIX,
    STATE_ATTR_DAYS,
    STATE_ATTR_NEXT_COLLECTION,
    DEVICE_CLASS,
    STATE_ATTR_COLOUR,
)

"""The UK Bin Collection Data integration."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from uk_bin_collection.uk_bin_collection.collect_data import UKBinCollectionApp

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass, config, async_add_entities
) -> None:
    """Set up the sensor platform."""
    _LOGGER.info(LOG_PREFIX + "Setting up UK Bin Collection Data platform.")
    _LOGGER.info(LOG_PREFIX + "Data Supplied: %s", config.data)

    name = config.data.get("name", "")
    timeout = config.data.get("timeout", 60)
    args = [
        config.data.get("council", ""),
        config.data.get("url", ""),
        *(
            f"--{key}={value}"
            for key, value in config.data.items()
            if key
            not in {
                "name",
                "council",
                "url",
                "skip_get_url",
                "headless",
                "local_browser",
                "timeout",
            }
        ),
    ]
    if config.data.get("skip_get_url", False):
        args.append("--skip_get_url")

    headless = config.data.get("headless", True)
    if headless is False:
        args.append("--not-headless")

    local_browser = config.data.get("local_browser", False)
    if local_browser:
        args.append("--local_browser")

    _LOGGER.info(f"{LOG_PREFIX} UKBinCollectionApp args: {args}")

    ukbcd = UKBinCollectionApp()
    ukbcd.set_args(args)

    coordinator = HouseholdBinCoordinator(hass, ukbcd, name, timeout=timeout)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        entity
        for bin_type in coordinator.data.keys()
        for entity in [
            UKBinCollectionDataSensor(coordinator, bin_type, f"{name}_{bin_type}"),  # Only 3 arguments here
            UKBinCollectionAttributeSensor(coordinator, bin_type, f"{name}_{bin_type}_colour", "Colour", f"{name}_{bin_type}"),
            UKBinCollectionAttributeSensor(coordinator, bin_type, f"{name}_{bin_type}_next_collection", "Next Collection Human Readble", f"{name}_{bin_type}"),
            UKBinCollectionAttributeSensor(coordinator, bin_type, f"{name}_{bin_type}_days", "Days Until Collection", f"{name}_{bin_type}"),
            UKBinCollectionAttributeSensor(coordinator, bin_type, f"{name}_{bin_type}_type", "Bin Type", f"{name}_{bin_type}"),
            UKBinCollectionAttributeSensor(coordinator, bin_type, f"{name}_{bin_type}_raw_next_collection", "Next Collection Date", f"{name}_{bin_type}"),
        ]
    )


class HouseholdBinCoordinator(DataUpdateCoordinator):
    """Household Bin Coordinator"""

    def __init__(self, hass, ukbcd, name, timeout=60):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="UK Bin Collection Data",
            update_interval=timedelta(hours=12),
        )
        self.ukbcd = ukbcd
        self.name = name
        self.timeout = timeout

    async def _async_update_data(self):
        async with async_timeout.timeout(self.timeout):
            _LOGGER.info(f"{LOG_PREFIX} UKBinCollectionApp Updating")
            data = await self.hass.async_add_executor_job(self.ukbcd.run)
        return get_latest_collection_info(json.loads(data))


def get_latest_collection_info(data) -> dict:
    """Process the bin collection data."""
    current_date = datetime.now()
    next_collection_dates = {}
    
    for bin_data in data["bins"]:
        bin_type = bin_data["type"]
        collection_date_str = bin_data["collectionDate"]
        collection_date = datetime.strptime(collection_date_str, "%d/%m/%Y")
        
        if collection_date.date() >= current_date.date():
            if bin_type in next_collection_dates:
                if collection_date < datetime.strptime(next_collection_dates[bin_type], "%d/%m/%Y"):
                    next_collection_dates[bin_type] = collection_date_str
            else:
                next_collection_dates[bin_type] = collection_date_str

    _LOGGER.info(f"{LOG_PREFIX} Next Collection Dates: {next_collection_dates}")
    return next_collection_dates


class UKBinCollectionDataSensor(CoordinatorEntity, SensorEntity):
    """Implementation of the UK Bin Collection Data sensor."""
    
    device_class = DEVICE_CLASS

    def __init__(self, coordinator, bin_type, device_id) -> None:
        """Initialize the main bin sensor."""
        super().__init__(coordinator)
        self._bin_type = bin_type
        self._device_id = device_id
        self.apply_values()

    @property
    def device_info(self):
        """Return device information for each bin."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"{self.coordinator.name} {self._bin_type}",
            "manufacturer": "UK Bin Collection",
            "model": "Bin Sensor",
            "sw_version": "1.0",
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updates from the coordinator."""
        self.apply_values()
        self.async_write_ha_state()

    def apply_values(self):
        """Apply values to the sensor."""
        self._next_collection = parser.parse(
            self.coordinator.data[self._bin_type], dayfirst=True
        ).date()
        now = dt_util.now()
        self._days = (self._next_collection - now.date()).days

        # Set the icon based on the bin type
        if "recycling" in self._bin_type.lower():
            self._icon = "mdi:recycle"
        elif "waste" in self._bin_type.lower():
            self._icon = "mdi:trash-can"
        else:
            self._icon = "mdi:delete"

        # Set the state based on the collection day
        if self._next_collection == now.date():
            self._state = "Today"
        elif self._next_collection == (now + timedelta(days=1)).date():
            self._state = "Tomorrow"
        else:
            self._state = f"In {self._days} days"

    @property
    def name(self):
        """Return the name of the bin."""
        return f"{self.coordinator.name} {self._bin_type}"

    @property
    def state(self):
        """Return the state of the bin."""
        return self._state


class UKBinCollectionAttributeSensor(CoordinatorEntity, SensorEntity):
    """Implementation of the attribute sensors (Colour, Next Collection, Days, Bin Type, Raw Next Collection)."""

    def __init__(self, coordinator, bin_type, unique_id, attribute_type, device_id) -> None:
        """Initialize the attribute sensor."""
        super().__init__(coordinator)
        self._bin_type = bin_type
        self._unique_id = unique_id
        self._attribute_type = attribute_type
        self._device_id = device_id  # Ensure the device_id is the same for all sensors of a bin

        # Set default icon and colour based on bin type
        if "recycling" in self._bin_type.lower():
            self._icon = "mdi:recycle"
            self._color = "green"
        elif "waste" in self._bin_type.lower():
            self._icon = "mdi:trash-can"
            self._color = "black"
        else:
            self._icon = "mdi:delete"
            self._color = "red"

    @property
    def name(self):
        """Return the name of the attribute sensor."""
        return f"{self.coordinator.name} {self._bin_type} {self._attribute_type}"

    @property
    def state(self):
        """Return the state based on the attribute type."""
        if self._attribute_type == "Colour":
            return self._color  # Return the colour of the bin
        elif self._attribute_type == "Next Collection Human Readble":
            return self.coordinator.data[self._bin_type]  # Already formatted next collection
        elif self._attribute_type == "Days Until Collection":
            next_collection = parser.parse(self.coordinator.data[self._bin_type], dayfirst=True).date()
            return (next_collection - datetime.now().date()).days
        elif self._attribute_type == "Bin Type":
            return self._bin_type  # Return the bin type for the Bin Type sensor
        elif self._attribute_type == "Next Collection Date":
            return self.coordinator.data[self._bin_type]  # Return the raw next collection date

    @property
    def icon(self):
        """Return the entity icon."""
        return self._icon

    @property
    def colour(self):
        """Return the bin colour."""
        return self._color

    @property
    def device_info(self):
        """Return device information for grouping sensors."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},  # Use the same device_id for all sensors of the same bin
            "name": f"{self.coordinator.name} {self._bin_type}",
            "manufacturer": "UK Bin Collection",
            "model": "Bin Sensor",
            "sw_version": "1.0",
        }

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return self._unique_id

