"""Support for UK Bin Collection Data sensors."""

from datetime import datetime, timedelta
import json
import logging
import asyncio
from typing import Any, Dict

from json import JSONDecodeError

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    LOG_PREFIX,
    STATE_ATTR_DAYS,
    STATE_ATTR_NEXT_COLLECTION,
    DEVICE_CLASS,
    STATE_ATTR_COLOUR,
)
from uk_bin_collection.uk_bin_collection.collect_data import UKBinCollectionApp

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the UK Bin Collection Data sensor platform."""
    _LOGGER.info(f"{LOG_PREFIX} Setting up UK Bin Collection Data platform.")

    name = config_entry.data.get("name")
    if not name:
        _LOGGER.error(f"{LOG_PREFIX} 'name' is missing in config entry.")
        raise ConfigEntryNotReady("Missing 'name' in configuration.")

    timeout = config_entry.data.get("timeout", 60)
    icon_color_mapping = config_entry.data.get("icon_color_mapping", "{}")

    # Validate 'timeout'
    try:
        timeout = int(timeout)
    except (ValueError, TypeError):
        _LOGGER.warning(
            f"{LOG_PREFIX} Invalid timeout value: {timeout}. Using default 60 seconds."
        )
        timeout = 60

    # Prepare arguments for UKBinCollectionApp
    args = build_ukbcd_args(config_entry.data)

    _LOGGER.debug(f"{LOG_PREFIX} UKBinCollectionApp args: {args}")

    # Initialize the UK Bin Collection Data application
    ukbcd = UKBinCollectionApp()
    ukbcd.set_args(args)

    # Initialize the data coordinator
    coordinator = HouseholdBinCoordinator(hass, ukbcd, name, timeout=timeout)

    try:
        await coordinator.async_refresh()
    except UpdateFailed as e:
        _LOGGER.error(f"{LOG_PREFIX} Unable to fetch initial data: {e}")
        raise ConfigEntryNotReady from e

    # Store the coordinator in Home Assistant's data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    # Create sensor entities
    entities = create_sensor_entities(coordinator, config_entry.entry_id, icon_color_mapping)

    # Register all sensor entities with Home Assistant
    async_add_entities(entities)

def build_ukbcd_args(config_data: Dict[str, Any]) -> list:
    """Build arguments list for UKBinCollectionApp."""
    excluded_keys = {
        "name",
        "council",
        "url",
        "skip_get_url",
        "headless",
        "local_browser",
        "timeout",
        "icon_color_mapping",
    }

    args = [config_data.get("council", ""), config_data.get("url", "")]

    # Add other arguments
    for key, value in config_data.items():
        if key in excluded_keys:
            continue
        if key == "web_driver":
            value = value.rstrip("/")
        args.append(f"--{key}={value}")

    # Add flags based on config options
    if config_data.get("skip_get_url", False):
        args.append("--skip_get_url")
    if not config_data.get("headless", True):
        args.append("--not-headless")
    if config_data.get("local_browser", False):
        args.append("--local_browser")

    return args


def create_sensor_entities(coordinator, entry_id, icon_color_mapping):
    """Create sensor entities based on coordinator data."""
    entities = []
    icon_color_map = load_icon_color_mapping(icon_color_mapping)

    for bin_type in coordinator.data.keys():
        device_id = f"{entry_id}_{bin_type}"

        # Main bin sensor
        entities.append(
            UKBinCollectionDataSensor(
                coordinator, bin_type, device_id, icon_color_map
            )
        )

        # Attribute sensors
        attributes = ["Colour", "Next Collection Human Readable", "Days Until Collection", "Bin Type", "Next Collection Date"]
        for attr in attributes:
            unique_id = f"{device_id}_{attr.lower().replace(' ', '_')}"
            entities.append(
                UKBinCollectionAttributeSensor(
                    coordinator, bin_type, unique_id, attr, device_id, icon_color_map
                )
            )

    # Add the Raw JSON Sensor
    entities.append(UKBinCollectionRawJSONSensor(coordinator, f"{entry_id}_raw_json", entry_id))

    return entities


def load_icon_color_mapping(icon_color_mapping: str) -> Dict[str, Any]:
    """Load and return the icon color mapping."""
    try:
        return json.loads(icon_color_mapping) if icon_color_mapping else {}
    except JSONDecodeError:
        _LOGGER.warning(
            f"{LOG_PREFIX} Invalid icon_color_mapping JSON: {icon_color_mapping}. Using default settings."
        )
        return {}


class HouseholdBinCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching and updating UK Bin Collection data."""

    def __init__(
        self,
        hass: HomeAssistant,
        ukbcd: UKBinCollectionApp,
        name: str,
        timeout: int = 60,
    ) -> None:
        """Initialize the data coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="UK Bin Collection Data",
            update_interval=timedelta(hours=12),
        )
        self.ukbcd = ukbcd
        self.name = name
        self.timeout = timeout

    async def _async_update_data(self) -> dict:
        """Fetch and process the latest bin collection data."""
        try:
            data = await asyncio.wait_for(
                self.hass.async_add_executor_job(self.ukbcd.run),
                timeout=self.timeout,
            )
            _LOGGER.debug(f"{LOG_PREFIX} Data fetched: {data}")
            parsed_data = json.loads(data)
            _LOGGER.debug(f"{LOG_PREFIX} Parsed data: {parsed_data}")
            return self.process_bin_data(parsed_data)
        except asyncio.TimeoutError as exc:
            _LOGGER.error(f"{LOG_PREFIX} Timeout while updating data: {exc}")
            raise UpdateFailed(f"Timeout while updating data: {exc}") from exc
        except JSONDecodeError as exc:
            _LOGGER.error(f"{LOG_PREFIX} JSON decode error: {exc}")
            raise UpdateFailed(f"JSON decode error: {exc}") from exc
        except Exception as exc:
            _LOGGER.exception(f"{LOG_PREFIX} Unexpected error: {exc}")
            raise UpdateFailed(f"Unexpected error: {exc}") from exc
    @staticmethod
    def process_bin_data(data: dict) -> dict:
        """Process raw data to determine the next collection dates."""
        current_date = dt_util.now().date()
        next_collection_dates = {}

        for bin_data in data.get("bins", []):
            bin_type = bin_data.get("type")
            collection_date_str = bin_data.get("collectionDate")

            if not bin_type or not collection_date_str:
                _LOGGER.warning(
                    f"{LOG_PREFIX} Missing 'type' or 'collectionDate' in bin data: {bin_data}"
                )
                continue

            try:
                collection_date = datetime.strptime(
                    collection_date_str, "%d/%m/%Y"
                ).date()
            except (ValueError, TypeError):
                _LOGGER.warning(
                    f"{LOG_PREFIX} Invalid date format for bin type '{bin_type}': '{collection_date_str}'."
                )
                continue

            # Update next collection date if it's sooner
            existing_date = next_collection_dates.get(bin_type)
            if (
                collection_date >= current_date
                and (not existing_date or collection_date < existing_date)
            ):
                next_collection_dates[bin_type] = collection_date

        _LOGGER.debug(f"{LOG_PREFIX} Next Collection Dates: {next_collection_dates}")
        return next_collection_dates


class UKBinCollectionDataSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity for individual bin collection data."""

    _attr_device_class = DEVICE_CLASS

    def __init__(
        self,
        coordinator: HouseholdBinCoordinator,
        bin_type: str,
        device_id: str,
        icon_color_mapping: Dict[str, Any],
    ) -> None:
        """Initialize the main bin sensor."""
        super().__init__(coordinator)
        self._bin_type = bin_type
        self._device_id = device_id
        self._icon_color_mapping = icon_color_mapping
        self._icon = self.get_icon()
        self._color = self.get_color()
        self._state = None
        self._next_collection = None
        self._days = None
        self.update_state()

    @property
    def device_info(self) -> dict:
        """Return device information for device registry."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"{self.coordinator.name} {self._bin_type}",
            "manufacturer": "UK Bin Collection",
            "model": "Bin Sensor",
            'sw_version': '1.0',
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updates from the coordinator and refresh sensor state."""
        self.update_state()
        self.async_write_ha_state()

    def update_state(self) -> None:
        """Update the sensor's state and attributes."""
        bin_date = self.coordinator.data.get(self._bin_type)
        if bin_date:
            self._next_collection = bin_date
            now = dt_util.now().date()
            self._days = (bin_date - now).days
            self._state = self.calculate_state()
        else:
            _LOGGER.warning(
                f"{LOG_PREFIX} Data for bin type '{self._bin_type}' is missing."
            )
            self._state = "Unknown"
            self._days = None
            self._next_collection = None

    def calculate_state(self) -> str:
        """Determine the state based on collection date."""
        now = dt_util.now().date()
        if self._next_collection == now:
            return "Today"
        elif self._next_collection == now + timedelta(days=1):
            return "Tomorrow"
        else:
            day_label = "day" if self._days == 1 else "days"
            return f"In {self._days} {day_label}"

    def get_icon(self) -> str:
        """Return the icon based on bin type or mapping."""
        return self._icon_color_mapping.get(self._bin_type, {}).get(
            "icon", self.get_default_icon()
        )

    def get_color(self) -> str:
        """Return the color based on bin type or mapping."""
        color = self._icon_color_mapping.get(self._bin_type, {}).get("color")
        if color is None:
            return "black"
        return color

    def get_default_icon(self) -> str:
        """Return a default icon based on the bin type."""
        bin_type_lower = self._bin_type.lower()
        if "recycling" in bin_type_lower:
            return "mdi:recycle"
        elif "waste" in bin_type_lower:
            return "mdi:trash-can"
        else:
            return "mdi:delete"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self.coordinator.name} {self._bin_type}"

    @property
    def state(self) -> str:
        """Return the current state of the sensor."""
        return self._state or "Unknown"

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        return self._icon

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes for the sensor."""
        return {
            STATE_ATTR_COLOUR: self._color,
            STATE_ATTR_NEXT_COLLECTION: self._next_collection.strftime("%d/%m/%Y")
            if self._next_collection
            else None,
            STATE_ATTR_DAYS: self._days,
        }

    @property
    def available(self) -> bool:
        """Return the availability of the sensor."""
        return self._state != "Unknown"

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the sensor."""
        return self._device_id


class UKBinCollectionAttributeSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity for additional attributes of a bin."""

    def __init__(
        self,
        coordinator: HouseholdBinCoordinator,
        bin_type: str,
        unique_id: str,
        attribute_type: str,
        device_id: str,
        icon_color_mapping: Dict[str, Any],
    ) -> None:
        """Initialize the attribute sensor."""
        super().__init__(coordinator)
        self._bin_type = bin_type
        self._unique_id = unique_id
        self._attribute_type = attribute_type
        self._device_id = device_id
        self._icon_color_mapping = icon_color_mapping
        self._icon = self.get_icon()
        self._color = self.get_color()

    @property
    def name(self) -> str:
        """Return the name of the attribute sensor."""
        return f"{self.coordinator.name} {self._bin_type} {self._attribute_type}"

    @property
    def state(self):
        """Return the state based on the attribute type."""
        if self._attribute_type == "Colour":
            return self._color
        elif self._attribute_type == "Bin Type":
            return self._bin_type
        elif self._attribute_type == "Next Collection Date":
            bin_date = self.coordinator.data.get(self._bin_type)
            return bin_date.strftime("%d/%m/%Y") if bin_date else "Unknown"
        elif self._attribute_type == "Next Collection Human Readable":
            return self.calculate_human_readable()
        elif self._attribute_type == "Days Until Collection":
            return self.calculate_days_until()
        else:
            _LOGGER.warning(
                f"{LOG_PREFIX} Undefined attribute type: {self._attribute_type}"
            )
            return "Undefined"

    def calculate_human_readable(self) -> str:
        """Calculate human-readable collection date."""
        bin_date = self.coordinator.data.get(self._bin_type)
        if not bin_date:
            return "Unknown"
        now = dt_util.now().date()
        days = (bin_date - now).days
        if days == 0:
            return "Today"
        elif days == 1:
            return "Tomorrow"
        else:
            day_label = "day" if days == 1 else "days"
            return f"In {days} {day_label}"

    def calculate_days_until(self) -> int:
        """Calculate days until collection."""
        bin_date = self.coordinator.data.get(self._bin_type)
        if not bin_date:
            return -1
        return (bin_date - dt_util.now().date()).days

    def get_icon(self) -> str:
        """Return the icon based on bin type or mapping."""
        return self._icon_color_mapping.get(self._bin_type, {}).get(
            "icon", self.get_default_icon()
        )

    def get_color(self) -> str:
        """Return the color based on bin type or mapping."""
        return self._icon_color_mapping.get(self._bin_type, {}).get("color", "black")

    def get_default_icon(self) -> str:
        """Return a default icon based on the bin type."""
        bin_type_lower = self._bin_type.lower()
        if "recycling" in bin_type_lower:
            return "mdi:recycle"
        elif "waste" in bin_type_lower:
            return "mdi:trash-can"
        else:
            return "mdi:delete"

    @property
    def icon(self) -> str:
        """Return the icon for the attribute sensor."""
        return self._icon

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes for the attribute sensor."""
        return {
            STATE_ATTR_COLOUR: self._color,
            STATE_ATTR_NEXT_COLLECTION: self.coordinator.data.get(self._bin_type),
        }

    @property
    def device_info(self) -> dict:
        """Return device information for device registry."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"{self.coordinator.name} {self._bin_type}",
            "manufacturer": "UK Bin Collection",
            "model": "Bin Sensor",
            'sw_version': '1.0',
        }

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the attribute sensor."""
        return self._unique_id

    @property
    def available(self) -> bool:
        """Return the availability of the attribute sensor."""
        return self.coordinator.last_update_success


class UKBinCollectionRawJSONSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity to hold the raw JSON data for bin collections."""

    def __init__(
        self,
        coordinator: HouseholdBinCoordinator,
        unique_id: str,
        name: str,
    ) -> None:
        """Initialize the raw JSON sensor."""
        super().__init__(coordinator)
        self._unique_id = unique_id
        self._name = f"{self.coordinator.name} Raw JSON"

    @property
    def name(self) -> str:
        """Return the name of the raw JSON sensor."""
        return self._name

    @property
    def state(self) -> str:
        """Return the raw JSON data as the state."""
        if not self.coordinator.data:
            return "{}"
        data = {
            bin_type: bin_date.strftime("%d/%m/%Y") if bin_date else None
            for bin_type, bin_date in self.coordinator.data.items()
        }
        return json.dumps(data)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the raw JSON sensor."""
        return self._unique_id

    @property
    def extra_state_attributes(self) -> dict:
        """Return the raw JSON data as an attribute."""
        return {"raw_data": self.coordinator.data or {}}

    @property
    def available(self) -> bool:
        """Return the availability of the raw JSON sensor."""
        return self.coordinator.last_update_success
