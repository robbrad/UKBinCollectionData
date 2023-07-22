"""Support for UK Bin Collection Dat sensors."""
from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity, SensorEntityDescription)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity
)

from . import UKBinCollectionDataUpdateCoordinator
from .const import (DOMAIN, _LOGGER, LOG_PREFIX)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback
) -> None:
    """Set up UK Bin Collection Data Sensors based on a config entry."""
    coordinator: UKBinCollectionDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.info(LOG_PREFIX + "Debug domain properties: %s", hass.data[DOMAIN])
    _LOGGER.info(LOG_PREFIX + "Debug entry properties: %s", hass.data[DOMAIN][entry.entry_id])

    # """Fetch new state data for the sensor."""
    # # Retrieve the data from hass.data using the entry_id
    # council_data = self.hass.data[DOMAIN].get(self._entry_id)
    #
    # # Update the sensor state with the next bin collection date
    # if council_data and "bins" in council_data:
    #     bins = council_data["bins"]
    #     if bins:
    #         next_collection_date = min(bins, key=lambda x: x["collectionDate"])["collectionDate"]
    #         self._state = next_collection_date

    # Get types
    BIN_TYPES: tuple[SensorEntityDescription, ...] = (
        SensorEntityDescription(
            key="next_collection",
            translation_key="next_collection",
            device_class=SensorDeviceClass.DATE,
        )
    )
    # for bin_type in hass.data[DOMAIN][entry.entry_id].data:
    #     BIN_TYPES += (
    #         SensorEntityDescription(
    #             key="next_collection" + bin_type,
    #             translation_key="next_collection" + bin_type,
    #             device_class=SensorDeviceClass.DATE,
    #         )
    #     )

    # Define entities
    entities: list[UKBinCollectionDataSensorEntity] = []
    entities.extend(
        UKBinCollectionDataSensorEntity(
            coordinator=coordinator,
            description=description,
            name="Test Name",
            service="test_service",
        )
        for description in BIN_TYPES
    )
    # Add entities
    async_add_entities(entities)


class UKBinCollectionDataSensorEntity(CoordinatorEntity[UKBinCollectionDataUpdateCoordinator], SensorEntity):
    """Implementation of the UK Bin Collection Data sensor."""

    _attr_has_entity_name = True

    def __init__(
            self,
            *,
            coordinator: UKBinCollectionDataUpdateCoordinator,
            description: SensorEntityDescription,
            name: str,
            service: "test_service"
    ) -> None:
        """Initialize UK Bin Collection Data sensor."""
        super().__init__(coordinator=coordinator)
        self._service_key = service

        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{service}_{description.key}"
        )

        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"{coordinator.config_entry.entry_id}_{service}")},
            manufacturer="UK Bin Collection Data",
            name=name,
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        value = getattr(
            self.coordinator.data[self._service_key], self.entity_description.key
        )
        if isinstance(value, str):
            return value.lower()
        return value
