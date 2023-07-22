from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, _LOGGER, LOG_PREFIX


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the entries."""
    async_add_entities([UkBinCollectionSensor(hass.data[DOMAIN], entry)])


class UkBinCollectionSensor(CoordinatorEntity, SensorEntity):
    """Implementation of the UK Bin Collection Data sensor."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry: SensorEntity):
        """Initialize the sensor."""
        super().__init__(coordinator)
        _LOGGER.info(LOG_PREFIX + "Setting up UK Bin Collection Data Sensor with coordinator: %s", coordinator)
        _LOGGER.info(LOG_PREFIX + "Setting up UK Bin Collection Data Sensor with entry: %s", entry)
        # self._id = self.coordinator.data["type"]
        # self._councilname = entry.data["council"]
        self._name = f"{self._councilname} bin"
        self._attr_unique_id = f"{entry.entry_id}_next_collection"

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
            "manufacturer": self._councilname,
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
