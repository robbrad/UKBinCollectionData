"""Support for UK Bin Collection Data sensors."""

from datetime import datetime, timedelta
import json
from json import JSONDecodeError
import logging

from dateutil import parser
import asyncio

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """
    Set up the UK Bin Collection Data sensor platform.
    """
    _LOGGER.info(f"{LOG_PREFIX} Setting up UK Bin Collection Data platform.")
    _LOGGER.debug(f"{LOG_PREFIX} Data Supplied: %s", config_entry.data)

    name = config_entry.data.get("name")
    if not name:
        _LOGGER.error(f"{LOG_PREFIX} 'name' is missing in config entry.")
        raise ConfigEntryNotReady("Missing 'name' in configuration.")

    timeout = config_entry.data.get("timeout", 60)
    icon_color_mapping = config_entry.data.get("icon_color_mapping", "{}")  # Default to empty JSON

    # Validate and sanitize 'timeout'
    try:
        timeout = int(timeout)
    except (ValueError, TypeError):
        _LOGGER.warning(f"{LOG_PREFIX} Invalid timeout value: {timeout}. Using default 60 seconds.")
        timeout = 60

    excluded_keys = {
        "name", "council", "url", "skip_get_url", "headless",
        "local_browser", "timeout", "icon_color_mapping",
    }

    # Construct arguments for UKBinCollectionApp
    args = [
        config_entry.data.get("council", ""),
        config_entry.data.get("url", ""),
        *(f"--{key}={value}" for key, value in config_entry.data.items() if key not in excluded_keys),
    ]

    if config_entry.data.get("skip_get_url", False):
        args.append("--skip_get_url")

    headless = config_entry.data.get("headless", True)
    if not headless:
        args.append("--not-headless")

    local_browser = config_entry.data.get("local_browser", False)
    if local_browser:
        args.append("--local_browser")

    _LOGGER.debug(f"{LOG_PREFIX} UKBinCollectionApp args: {args}")

    # Initialize the UK Bin Collection Data application
    ukbcd = UKBinCollectionApp()
    ukbcd.set_args(args)

    # Initialize the data coordinator
    coordinator = HouseholdBinCoordinator(
        hass, ukbcd, name, config_entry, timeout=timeout
    )

    try:
        await coordinator.async_refresh()
    except UpdateFailed as e:
        _LOGGER.error(f"{LOG_PREFIX} Unable to fetch initial data: {e}")
        raise ConfigEntryNotReady from e

    # Store the coordinator in Home Assistant's data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    entities = []
    for bin_type in coordinator.data.keys():
        device_id = f"{name}_{bin_type}"
        entities.extend([
            UKBinCollectionDataSensor(coordinator, bin_type, device_id, icon_color_mapping),
            UKBinCollectionAttributeSensor(
                coordinator,
                bin_type,
                f"{device_id}_colour",
                "Colour",
                device_id,
                icon_color_mapping,
            ),
            UKBinCollectionAttributeSensor(
                coordinator,
                bin_type,
                f"{device_id}_next_collection",
                "Next Collection Human Readable",
                device_id,
                icon_color_mapping,
            ),
            UKBinCollectionAttributeSensor(
                coordinator,
                bin_type,
                f"{device_id}_days",
                "Days Until Collection",
                device_id,
                icon_color_mapping,
            ),
            UKBinCollectionAttributeSensor(
                coordinator,
                bin_type,
                f"{device_id}_type",
                "Bin Type",
                device_id,
                icon_color_mapping,
            ),
            UKBinCollectionAttributeSensor(
                coordinator,
                bin_type,
                f"{device_id}_raw_next_collection",
                "Next Collection Date",
                device_id,
                icon_color_mapping,
            ),
        ])

    # Add the Raw JSON Sensor
    entities.append(UKBinCollectionRawJSONSensor(coordinator, f"{name}_raw_json", name))

    # Register all sensor entities with Home Assistant
    async_add_entities(entities)



class HouseholdBinCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching and updating UK Bin Collection data."""

    def __init__(
        self,
        hass: HomeAssistant,
        ukbcd: UKBinCollectionApp,
        name: str,
        config_entry: ConfigEntry,
        timeout: int = 60,
    ) -> None:
        """
        Initialize the data coordinator.

        Args:
            hass: Home Assistant instance.
            ukbcd: Instance of UKBinCollectionApp to fetch data.
            name: Name of the sensor.
            config_entry: Configuration entry.
            timeout: Timeout for data fetching in seconds.
        """
        super().__init__(
            hass,
            _LOGGER,
            name="UK Bin Collection Data",
            update_interval=timedelta(hours=12),
        )
        self.ukbcd = ukbcd
        self.name = name
        self.timeout = timeout
        self.config_entry = config_entry

    async def _async_update_data(self) -> dict:
        """Fetch and process the latest bin collection data."""
        try:
            async with asyncio.timeout(self.timeout):
                _LOGGER.debug(f"{LOG_PREFIX} UKBinCollectionApp Updating")
                data = await self.hass.async_add_executor_job(self.ukbcd.run)
                _LOGGER.debug(f"{LOG_PREFIX} Data fetched: {data}")
            parsed_data = json.loads(data)
            _LOGGER.debug(f"{LOG_PREFIX} Parsed data: {parsed_data}")
            return get_latest_collection_info(parsed_data) if parsed_data else {}
        except asyncio.TimeoutError as exc:
            _LOGGER.error(f"{LOG_PREFIX} Timeout while updating data: {exc}")
            raise UpdateFailed(f"Timeout while updating data: {exc}") from exc
        except JSONDecodeError as exc:
            _LOGGER.error(f"{LOG_PREFIX} JSON decode error: {exc}")
            raise UpdateFailed(f"JSON decode error: {exc}") from exc
        except Exception as exc:
            _LOGGER.exception(f"{LOG_PREFIX} Unexpected error: {exc}")
            raise UpdateFailed(f"Unexpected error: {exc}") from exc


def get_latest_collection_info(data: dict) -> dict:
    """
    Process the raw bin collection data to determine the next collection dates.

    Args:
        data: Raw data from UK Bin Collection API.

    Returns:
        A dictionary mapping bin types to their next collection dates.
    """
    current_date = dt_util.now()
    next_collection_dates = {}

    for bin_data in data.get("bins", []):
        bin_type = bin_data.get("type")
        collection_date_str = bin_data.get("collectionDate")

        if not bin_type or not collection_date_str:
            _LOGGER.warning(f"{LOG_PREFIX} Missing 'type' or 'collectionDate' in bin data: {bin_data}")
            continue  # Skip entries with missing fields

        try:
            collection_date = datetime.strptime(collection_date_str, "%d/%m/%Y")
        except (ValueError, TypeError):
            _LOGGER.warning(f"{LOG_PREFIX} Invalid date format for bin type '{bin_type}': '{collection_date_str}'.")
            continue  # Skip entries with invalid date formats

        # Ensure the collection date is today or in the future
        if collection_date.date() >= current_date.date():
            existing_date_str = next_collection_dates.get(bin_type)
            if (not existing_date_str) or (collection_date < datetime.strptime(existing_date_str, "%d/%m/%Y")):
                next_collection_dates[bin_type] = collection_date_str

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
        icon_color_mapping: str = "{}",
    ) -> None:
        """
        Initialize the main bin sensor.

        Args:
            coordinator: Data coordinator instance.
            bin_type: Type of the bin (e.g., recycling, waste).
            device_id: Unique identifier for the device.
            icon_color_mapping: JSON string mapping bin types to icons and colors.
        """
        super().__init__(coordinator)
        self._bin_type = bin_type
        self._device_id = device_id
        self._state = None
        self._next_collection = None
        self._days = None
        self._icon = None
        self._color = None

        # Load icon and color mappings
        try:
            self._icon_color_mapping = json.loads(icon_color_mapping) if icon_color_mapping else {}
        except JSONDecodeError:
            _LOGGER.warning(
                f"{LOG_PREFIX} Invalid icon_color_mapping JSON: {icon_color_mapping}. Using default settings."
            )
            self._icon_color_mapping = {}

        self.apply_values()

    @property
    def device_info(self) -> dict:
        """Return device information for device registry."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"{self.coordinator.name} {self._bin_type}",
            "manufacturer": "UK Bin Collection",
            "model": "Bin Sensor",
            "sw_version": "1.0",
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updates from the coordinator and refresh sensor state."""
        self.apply_values()
        self.async_write_ha_state()

    def apply_values(self) -> None:
        """Apply the latest data to the sensor's state and attributes."""
        bin_data = self.coordinator.data.get(self._bin_type)
        if bin_data:
            try:
                self._next_collection = parser.parse(bin_data, dayfirst=True).date()
                now = dt_util.now().date()
                self._days = (self._next_collection - now).days

                # Set icon and color based on mapping or defaults
                bin_mapping = self._icon_color_mapping.get(self._bin_type, {})
                self._icon = bin_mapping.get("icon") or self.get_default_icon()
                self._color = bin_mapping.get("color") or "black"

                # Determine state based on collection date
                if self._next_collection == now:
                    self._state = "Today"
                elif self._next_collection == now + timedelta(days=1):
                    self._state = "Tomorrow"
                else:
                    day_label = "day" if self._days == 1 else "days"
                    self._state = f"In {self._days} {day_label}"
            except (ValueError, TypeError) as exc:
                _LOGGER.warning(
                    f"{LOG_PREFIX} Error parsing collection date for '{self._bin_type}': {exc}"
                )
                self._state = "Unknown"
                self._next_collection = None
                self._days = None
                self._icon = "mdi:delete-alert"
                self._color = "grey"
        else:
            _LOGGER.warning(f"{LOG_PREFIX} Data for bin type '{self._bin_type}' is missing.")
            self._state = "Unknown"
            self._next_collection = None
            self._days = None
            self._icon = "mdi:delete-alert"
            self._color = "grey"

    def get_default_icon(self) -> str:
        """Return a default icon based on the bin type."""
        if "recycling" in self._bin_type.lower():
            return "mdi:recycle"
        elif "waste" in self._bin_type.lower():
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
        return self._state if self._state else "Unknown"

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        return self._icon if self._icon else "mdi:alert"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes for the sensor."""
        return {
            STATE_ATTR_COLOUR: self._color,
            STATE_ATTR_NEXT_COLLECTION: self._next_collection.strftime("%d/%m/%Y") if self._next_collection else None,
            STATE_ATTR_DAYS: self._days,
        }

    @property
    def color(self) -> str:
        """Return the color associated with the bin."""
        return self._color if self._color else "grey"

    @property
    def available(self) -> bool:
        """Return the availability of the sensor."""
        return self._state not in [None, "Unknown"]

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
        icon_color_mapping: str = "{}",
    ) -> None:
        """
        Initialize the attribute sensor.

        Args:
            coordinator: Data coordinator instance.
            bin_type: Type of the bin (e.g., recycling, waste).
            unique_id: Unique identifier for the sensor.
            attribute_type: The specific attribute this sensor represents.
            device_id: Unique identifier for the device.
            icon_color_mapping: JSON string mapping bin types to icons and colors.
        """
        super().__init__(coordinator)
        self._bin_type = bin_type
        self._unique_id = unique_id
        self._attribute_type = attribute_type
        self._device_id = device_id

        # Load icon and color mappings
        try:
            self._icon_color_mapping = json.loads(icon_color_mapping) if icon_color_mapping else {}
        except JSONDecodeError:
            _LOGGER.warning(
                f"{LOG_PREFIX} Invalid icon_color_mapping JSON: {icon_color_mapping}. Using default settings."
            )
            self._icon_color_mapping = {}

        # Set icon and color based on mapping or defaults
        bin_mapping = self._icon_color_mapping.get(self._bin_type, {})
        self._icon = bin_mapping.get("icon") or self.get_default_icon()
        self._color = bin_mapping.get("color") or "black"

    def get_default_icon(self) -> str:
        """Return a default icon based on the bin type."""
        if "recycling" in self._bin_type.lower():
            return "mdi:recycle"
        elif "waste" in self._bin_type.lower():
            return "mdi:trash-can"
        else:
            return "mdi:delete"

    @property
    def name(self) -> str:
        """Return the name of the attribute sensor."""
        return f"{self.coordinator.name} {self._bin_type} {self._attribute_type}"

    @property
    def state(self):
        """Return the state based on the attribute type."""
        bin_data = self.coordinator.data.get(self._bin_type)
        if not bin_data:
            return "Unknown"

        if self._attribute_type == "Colour":
            return self._color

        elif self._attribute_type == "Next Collection Human Readable":
            try:
                collection_date = parser.parse(bin_data, dayfirst=True).date()
                now = dt_util.now().date()
                if collection_date == now:
                    return "Today"
                elif collection_date == now + timedelta(days=1):
                    return "Tomorrow"
                else:
                    days = (collection_date - now).days
                    day_label = "day" if days == 1 else "days"
                    return f"In {days} {day_label}"
            except (ValueError, TypeError):
                return "Invalid Date"

        elif self._attribute_type == "Days Until Collection":
            try:
                next_collection = parser.parse(bin_data, dayfirst=True).date()
                return (next_collection - dt_util.now().date()).days
            except (ValueError, TypeError):
                return "Invalid Date"

        elif self._attribute_type == "Bin Type":
            return self._bin_type

        elif self._attribute_type == "Next Collection Date":
            return bin_data

        else:
            _LOGGER.warning(f"{LOG_PREFIX} Undefined attribute type: {self._attribute_type}")
            return "Undefined"

    @property
    def icon(self) -> str:
        """Return the icon for the attribute sensor."""
        return self._icon

    @property
    def color(self) -> str:
        """Return the color associated with the attribute sensor."""
        return self._color

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
            "sw_version": "1.0",
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
        """
        Initialize the raw JSON sensor.

        Args:
            coordinator: Data coordinator instance.
            unique_id: Unique identifier for the sensor.
            name: Base name for the sensor.
        """
        super().__init__(coordinator)
        self._unique_id = unique_id
        self._name = name

    @property
    def name(self) -> str:
        """Return the name of the raw JSON sensor."""
        return f"{self._name} Raw JSON"

    @property
    def state(self) -> str:
        """Return the raw JSON data as the state."""
        return json.dumps(self.coordinator.data) if self.coordinator.data else "{}"

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the raw JSON sensor."""
        return self._unique_id

    @property
    def extra_state_attributes(self) -> dict:
        """Return the raw JSON data as an attribute."""
        return {
            "raw_data": self.coordinator.data or {}
        }

    @property
    def available(self) -> bool:
        """Return the availability of the raw JSON sensor."""
        return self.coordinator.last_update_success
