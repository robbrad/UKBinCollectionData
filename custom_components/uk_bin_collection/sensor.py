"""Support for UK Bin Collection Dat sensors."""
from datetime import timedelta, datetime
from dateutil import parser
import async_timeout


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

    args = [
        config.data.get("council", ""),
        config.data.get("url", ""),
        *(
            f"--{key}={value}"
            for key, value in config.data.items()
            if key not in {"name", "council", "url", "skip_get_url"}
        ),
    ]
    if config.data.get("skip_get_url", False):
        args.append("--skip_get_url")

    _LOGGER.info(f"{LOG_PREFIX} UKBinCollectionApp args: {args}")

    ukbcd = UKBinCollectionApp()
    ukbcd.set_args(args)
    _LOGGER.info(f"{LOG_PREFIX} Args set")

    coordinator = HouseholdBinCoordinator(hass, ukbcd)

    _LOGGER.info(f"{LOG_PREFIX} UKBinCollectionApp Init Refresh")
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info(f"{LOG_PREFIX} UKBinCollectionApp Init Refresh complete")

    async_add_entities(
        UKBinCollectionDataSensor(coordinator, idx)
        for idx, ent in enumerate(coordinator.data)
    )


def get_latest_collection_info(data) -> list:
    # Get the current date
    current_date = datetime.now()

    # Create a list to store the next collection date for each type
    next_collection_dates = []

    # Iterate through each bin in the data
    for bin_data in data["bins"]:
        bin_type = bin_data["type"]
        collection_date_str = bin_data["collectionDate"]

        # Convert the collection date from string to datetime object
        collection_date = datetime.strptime(collection_date_str, "%d/%m/%Y")

        # Only consider collection dates that are greater than or equal to the current date
        if collection_date >= current_date:
            # Find the index of the bin type in the list
            index = next(
                (
                    i
                    for i, bin_info in enumerate(next_collection_dates)
                    if bin_info["type"] == bin_type
                ),
                None,
            )

            # If the bin type is not in the list, add it; otherwise, update its collection date if needed
            if index is None:
                next_collection_dates.append(
                    {"type": bin_type, "collectionDate": collection_date_str}
                )
            else:
                if collection_date < datetime.strptime(
                    next_collection_dates[index]["collectionDate"], "%d/%m/%Y"
                ):
                    next_collection_dates[index]["collectionDate"] = collection_date_str
    _LOGGER.info(f"{LOG_PREFIX} Next Collection Dates: {next_collection_dates}")
    return next_collection_dates


class HouseholdBinCoordinator(DataUpdateCoordinator):
    """Household Bin Coordinator"""

    def __init__(self, hass, ukbcd):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Bin Collection Manchester Council",
            update_interval=timedelta(seconds=10),
        )
        _LOGGER.info(f"{LOG_PREFIX} UKBinCollectionApp Init")
        self.ukbcd = ukbcd

    async def _async_update_data(self):
        async with async_timeout.timeout(10):
            _LOGGER.info(f"{LOG_PREFIX} UKBinCollectionApp Updating")

            # data = await self.hass.async_add_executor_job(
            #    self.ukbcd.run()
            # )
            data = {
                "bins": [
                    {
                        "type": "Empty Standard Mixed Recycling",
                        "collectionDate": "29/07/2023",
                    },
                    {
                        "type": "Empty Standard Garden Waste",
                        "collectionDate": "29/07/2023",
                    },
                    {
                        "type": "Empty Standard General Waste",
                        "collectionDate": "06/08/2023",
                    },
                    {
                        "type": "Empty Standard Garden Waste",
                        "collectionDate": "12/08/2023",
                    },
                    {
                        "type": "Empty Standard Mixed Recycling",
                        "collectionDate": "12/08/2023",
                    },
                    {
                        "type": "Empty Standard General Waste",
                        "collectionDate": "19/08/2023",
                    },
                    {
                        "type": "Empty Standard Mixed Recycling",
                        "collectionDate": "26/08/2023",
                    },
                    {
                        "type": "Empty Standard Garden Waste",
                        "collectionDate": "26/08/2023",
                    },
                    {
                        "type": "Empty Standard General Waste",
                        "collectionDate": "02/09/2023",
                    },
                    {
                        "type": "Empty Standard Mixed Recycling",
                        "collectionDate": "09/09/2023",
                    },
                ]
            }
            _LOGGER.info(f"{LOG_PREFIX} UKBinCollectionApp: {data}")

        return get_latest_collection_info(data)


class UKBinCollectionDataSensor(CoordinatorEntity, SensorEntity):
    """Implementation of the UK Bin Collection Data sensor."""

    # _attr_device_class = SensorDeviceClass.DATE
    device_class = DEVICE_CLASS

    def __init__(self, coordinator, idx) -> None:
        """Initialize a UK Bin Collection Data sensor."""
        super().__init__(coordinator)
        self.idx = idx
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
        _LOGGER.info(f"{LOG_PREFIX} Applying values for sensor {self.idx}")
        bin_info = self.coordinator.data[self.idx]
        self._id = bin_info["type"]
        self._name = bin_info["type"]
        self._next_collection = parser.parse(bin_info["collectionDate"]).date()
        self._hidden = False
        self._icon = "mdi:trash-can"
        self._colour = "red"
        self._state = "unknown"

        _LOGGER.info(
            f"{LOG_PREFIX} Data Stored in self.next_collection: {self._next_collection}"
        )
        _LOGGER.info(f"{LOG_PREFIX} Data Stored in self.type: {self._name}")

        now = dt_util.now()
        next_collection = parser.parse(bin_info["collectionDate"], dayfirst=True).date()
        this_week_start = now.date() - timedelta(days=now.weekday())
        this_week_end = this_week_start + timedelta(days=6)
        next_week_start = this_week_end + timedelta(days=1)
        next_week_end = next_week_start + timedelta(days=6)

        self._days = (next_collection - now.date()).days
        _LOGGER.info(f"{LOG_PREFIX} _days: {self._days}")

        if next_collection == now.date():
            self._state = "Today"
        elif next_collection == (now + timedelta(days=1)).date():
            self._state = "Tomorrow"
        elif next_collection >= this_week_start and next_collection <= this_week_end:
            self._state = f"This Week: {next_collection.strftime('%A')}"
        elif next_collection >= next_week_start and next_collection <= next_week_end:
            self._state = f"Next Week: {next_collection.strftime('%A')}"
        elif next_collection > next_week_end:
            self._state = f"Future: {next_collection}"
        elif next_collection < now.date():
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
