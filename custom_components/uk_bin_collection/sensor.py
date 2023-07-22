"""Support for UK Bin Collection Dat sensors."""
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import UKBinCollectionDataUpdateCoordinator
from .const import DOMAIN, _LOGGER, LOG_PREFIX


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback
) -> None:
    """Set up UK Bin Collection Data entry."""
    coordinator: UKBinCollectionDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        UKBinCollectionDataSensor(coordinator, "Next Collection")
    ]
    # Add sensors for each collection type (e.g. next_collection_refuse)
    # for collection_type in [collection["type"] for collection in coordinator.data]:
    #     sensors.append(UKBinCollectionDataSensor(coordinator, f"next_collection_{collection_type.capitalize()}"))

    async_add_entities(sensors, True)


class UKBinCollectionDataSensor(CoordinatorEntity[UKBinCollectionDataUpdateCoordinator], SensorEntity):
    """Implementation of the UK Bin Collection Data sensor."""

    # _attr_device_class = SensorDeviceClass.DATE

    def __init__(
            self,
            coordinator: UKBinCollectionDataUpdateCoordinator,
            type: str
    ) -> None:
        """Initialize a UK Bin Collection Data sensor."""
        super().__init__(coordinator)
        self.type = type
        self._name = f"{coordinator.name} {self.type}"
        self._attr_name = f"{coordinator.name} {self.type}"
        self._attr_unique_id = f"{coordinator.name}_{self.type}"
        # Set state
        _LOGGER.info(LOG_PREFIX + "Sensor coordinator data: %s", coordinator.data)
        if coordinator.data and "bins" in coordinator.data:
            bins = coordinator.data["bins"]
            if bins:
                if self.type != "Next Collection":
                    bins = [c for c in bins if c.type == self.type]
                self._state = datetime.strptime(
                    min(bins, key=lambda x: x["collectionDate"])["collectionDate"],
                    "%d/%m/%Y",
                ).date()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state
