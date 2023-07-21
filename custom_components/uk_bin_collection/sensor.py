import asyncio
import json
from typing import Any, Dict

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorEntity
from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady  # Add the missing import
from homeassistant.core import HomeAssistant

# Make sure the 'uk_bin_collection' library is installed for this import to work
from uk_bin_collection.uk_bin_collection import collect_data

DEFAULT_NAME = "UK Bin Collection Data"
DOMAIN = "uk_bin_collection"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UK Bin Collection Data config entry."""
    data = entry.data
    args = [
        data["council"],
        data["url"],
        *(f"-{key[0]}={value}" for key, value in data.items() if key not in {"council", "url"}),
    ]

    try:
        # Get the JSON string from collect_data(args)
        json_string = await collect_data(args)

        # Parse the JSON string into a Python dictionary
        council_data = json.loads(json_string)
    except Exception as err:
        raise ConfigEntryNotReady from err

    hass.data[DOMAIN][entry.entry_id] = council_data

    # Set up the sensor entity to display the next bin collection date
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, SENSOR_DOMAIN)
    )

    return True


class UkBinCollectionSensor(SensorEntity):
    """Representation of a UK Bin Collection Data."""

    def __init__(self, entry_id: str, name: str):
        """Initialize the sensor."""
        self._entry_id = entry_id
        self._name = name
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_info(self):
        """Return device information about the sensor."""
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": self._name,
            "manufacturer": "Your Manufacturer",
        }

    async def async_update(self):
        """Fetch new state data for the sensor."""
        # Retrieve the data from hass.data using the entry_id
        council_data = self.hass.data[DOMAIN].get(self._entry_id)

        # Update the sensor state with the next bin collection date
        if council_data and "bins" in council_data:
            bins = council_data["bins"]
            if bins:
                next_collection_date = min(bins, key=lambda x: x["collectionDate"])["collectionDate"]
                self._state = next_collection_date


# Config Flow for UK Bin Collection
config_entries.HANDLERS.register(DOMAIN, "UK Bin Collection Data", lambda _: True)
