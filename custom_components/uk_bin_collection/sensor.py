"""Support for UK Bin Collection Dat sensors."""
from datetime import timedelta, datetime
from dateutil import parser
import async_timeout
import json


from homeassistant.components.sensor import SensorEntity

from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
import homeassistant.util.dt as dt_util
from .const import (
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
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    _LOGGER.info(LOG_PREFIX + "Setting up UK Bin Collection Data platform.")
    _LOGGER.info(LOG_PREFIX + "Data Supplied: %s", config.data)

    name = config.data.get("name", "")
    args = [
        config.data.get("council", ""),
        config.data.get("url", ""),
        *(
            f"--{key}={value}"
            for key, value in config.data.items()
            if key not in {"name", "council", "url", "skip_get_url", "headless"}
        ),
    ]
    if config.data.get("skip_get_url", False):
        args.append("--skip_get_url")

    #Run with the --not-headless switch
    if config.data.get("headless", True):
        headless = config.data.get("headless")
        if headless:
            args.append("--headless")
        else:
            args.append("--not-headless")

    _LOGGER.info(f"{LOG_PREFIX} UKBinCollectionApp args: {args}")

    ukbcd = UKBinCollectionApp()
    ukbcd.set_args(args)
    _LOGGER.info(f"{LOG_PREFIX} Args set")

    coordinator = HouseholdBinCoordinator(hass, ukbcd, name)

    _LOGGER.info(f"{LOG_PREFIX} UKBinCollectionApp Init Refresh")
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info(f"{LOG_PREFIX} UKBinCollectionApp Init Refresh complete")

    async_add_entities(
        UKBinCollectionDataSensor(coordinator, bin_type)
        for bin_type in coordinator.data.keys()
    )


def get_latest_collection_info(data) -> dict:
    # Get the current date
    current_date = datetime.now()

    # Create a dict to store the next collection date for each type
    next_collection_dates = {}
    _LOGGER.info(f"{LOG_PREFIX} Data Supplied: {data} and type of data is {type(data)}")
    # Iterate through each bin in the data
    for bin_data in data["bins"]:
        bin_type = bin_data["type"]
        collection_date_str = bin_data["collectionDate"]

        # Convert the collection date from string to datetime object
        collection_date = datetime.strptime(collection_date_str, "%d/%m/%Y")

        # Only consider collection dates that are greater than or equal to the current date
        if collection_date.date() >= current_date.date():
            # If the bin type is in the dict, update its collection date if needed; otherwise, add it
            if bin_type in next_collection_dates:
                if collection_date < datetime.strptime(
                    next_collection_dates[bin_type], "%d/%m/%Y"
                ):
                    next_collection_dates[bin_type] = collection_date_str
            else:
                next_collection_dates[bin_type] = collection_date_str

    _LOGGER.info(f"{LOG_PREFIX} Next Collection Dates: {next_collection_dates}")
    return next_collection_dates


class HouseholdBinCoordinator(DataUpdateCoordinator):
    """Household Bin Coordinator"""

    def __init__(self, hass, ukbcd, name):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="UK Bin Collection Data",
            update_interval=timedelta(hours=12),
        )
        _LOGGER.info(f"{LOG_PREFIX} UKBinCollectionApp Init")
        self.ukbcd = ukbcd
        self.name = name

    async def _async_update_data(self):
        async with async_timeout.timeout(60) as cm:
            _LOGGER.info(f"{LOG_PREFIX} UKBinCollectionApp Updating")

            data = await self.hass.async_add_executor_job(self.ukbcd.run)

            _LOGGER.info(f"{LOG_PREFIX} UKBinCollectionApp: {data}")

        if cm.expired:
            _LOGGER.warning(
                f"{LOG_PREFIX} UKBinCollectionApp timeout expired during run"
            )

        return get_latest_collection_info(json.loads(data))


class UKBinCollectionDataSensor(CoordinatorEntity, SensorEntity):
    """Implementation of the UK Bin Collection Data sensor."""

    device_class = DEVICE_CLASS

    def __init__(self, coordinator, bin_type) -> None:
        """Initialize a UK Bin Collection Data sensor."""
        super().__init__(coordinator)
        self._bin_type = bin_type
        self.apply_values()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.apply_values()
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the bins."""
        return {
            STATE_ATTR_COLOUR: self._colour,
            STATE_ATTR_NEXT_COLLECTION: self._next_collection,
            STATE_ATTR_DAYS: self._days,
        }

    def apply_values(self):
        _LOGGER.info(f"{LOG_PREFIX} Applying values for sensor {self._bin_type}")
        name = self._bin_type
        if self.coordinator.name != "":
            name = "{} {}".format(self.coordinator.name, self._bin_type)
        self._id = name
        self._name = name
        self._next_collection = parser.parse(
            self.coordinator.data[self._bin_type], dayfirst=True
        ).date()
        self._hidden = False
        self._icon = "mdi:trash-can"
        self._colour = "red"
        self._state = "unknown"

        _LOGGER.info(
            f"{LOG_PREFIX} Data Stored in self.next_collection: {self._next_collection}"
        )
        _LOGGER.info(f"{LOG_PREFIX} Data Stored in self.name: {self._name}")

        now = dt_util.now()
        this_week_start = now.date() - timedelta(days=now.weekday())
        this_week_end = this_week_start + timedelta(days=6)
        next_week_start = this_week_end + timedelta(days=1)
        next_week_end = next_week_start + timedelta(days=6)

        self._days = (self._next_collection - now.date()).days
        _LOGGER.info(f"{LOG_PREFIX} _days: {self._days}")

        if self._next_collection == now.date():
            self._state = "Today"
        elif self._next_collection == (now + timedelta(days=1)).date():
            self._state = "Tomorrow"
        elif (
            self._next_collection >= this_week_start
            and self._next_collection <= this_week_end
        ):
            self._state = f"This Week: {self._next_collection.strftime('%A')}"
        elif (
            self._next_collection >= next_week_start
            and self._next_collection <= next_week_end
        ):
            self._state = f"Next Week: {self._next_collection.strftime('%A')}"
        elif self._next_collection > next_week_end:
            self._state = f"Future: {self._next_collection}"
        elif self._next_collection < now.date():
            self._state = "Past"
        else:
            self._state = "Unknown"

        _LOGGER.info(f"{LOG_PREFIX} State of the sensor: {self._state}")

    @property
    def name(self):
        """Return the name of the bin."""
        return self._name

    @property
    def hidden(self):
        """Return the hidden attribute."""
        return self._hidden

    @property
    def state(self):
        """Return the state of the bin."""
        return self._state

    @property
    def days(self):
        """Return the remaining days until the collection."""
        return self._days

    @property
    def next_collection(self):
        """Return the next collection of the bin."""
        return self._next_collection

    @property
    def icon(self):
        """Return the entity icon."""
        return self._icon

    @property
    def colour(self):
        """Return the entity icon."""
        return self._colour

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return self._id

    @property
    def bin_type(self):
        """Return the bin type."""
        return self._bin_type
