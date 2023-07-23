"""The UK Bin Collection Data integration."""
import json
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

# Make sure the 'uk_bin_collection' library is installed for this import to work
from uk_bin_collection.uk_bin_collection.collect_data import UKBinCollectionApp
from .const import DOMAIN, _LOGGER, LOG_PREFIX, PLATFORMS, SCAN_INTERVAL


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UK Bin Collection Data from a config entry."""
    _LOGGER.info(LOG_PREFIX + "Data Supplied: %s", entry.data)
    council_name = entry.data.get("council", "unknown council")
    _LOGGER.info(LOG_PREFIX + "Setting up UK Bin Collection Data for council: %s", council_name)

    coordinator = UKBinCollectionDataUpdateCoordinator(hass, entry.data)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    if entry.unique_id is None:
        name = entry.data["name"]
        hass.config_entries.async_update_entry(entry, unique_id=f"{name}")

    async def _async_finish_startup(_):
        await coordinator.async_refresh()
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async_at_started(hass, _async_finish_startup)
    _LOGGER.info(LOG_PREFIX + "Successfully set up UK Bin Collection Data for council: %s", council_name)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


class UKBinCollectionDataUpdateCoordinator(DataUpdateCoordinator[object | None]):
    """Class to manage fetching UK Bin Collection Data council data."""

    def __init__(self, hass, data):
        """Initialize global UK Bin Collection Data updater."""
        self._hass = hass
        self._data = data
        self.name = data["name"]
        self.args = [
            self._data.get("council", ""),
            self._data.get("url", ""),
            *(f"--{key}={value}" for key, value in self._data.items() if
              key not in {"name", "council", "url", "skip_get_url"}),
        ]
        if "skip_get_url" in self._data:
            self.args.append("--skip_get_url")
        self.ukbcd = UKBinCollectionApp()
        self.ukbcd.set_args(self.args)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.name}",
            update_interval=SCAN_INTERVAL
        )

    async def _async_update_data(self) -> object | None:
        """Fetch council data."""
        try:
            _LOGGER.info(LOG_PREFIX + "Collecting data for council: %s", self._data["council"])
            # Run UKBCD and get the JSON string
            json_string = await self._hass.async_add_executor_job(self.ukbcd.run)

            # Parse the JSON string into a Python dictionary
            council_data = json.loads(json_string)

            # Sort data by collection date
            council_data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
            )
            _LOGGER.info(LOG_PREFIX + "Council Data: %s", council_data)
            return council_data
        except Exception as err:
            _LOGGER.error(LOG_PREFIX + "Failed to collect data for council: %s", self._data["council"], exc_info=True)
            return None
