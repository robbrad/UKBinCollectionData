"""The UK Bin Collection Data integration."""
import json
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

# Make sure the 'uk_bin_collection' library is installed for this import to work
from uk_bin_collection.uk_bin_collection.collect_data import UKBinCollectionApp
from .const import DOMAIN, _LOGGER, LOG_PREFIX, PLATFORMS, SCAN_INTERVAL


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UK Bin Collection Data from a config entry."""
    data = entry.data
    _LOGGER.info(LOG_PREFIX + "Data Supplied: %s", data)
    council_name = data.get("council", "unknown council")
    _LOGGER.info(LOG_PREFIX + "Setting up UK Bin Collection Data for council: %s", council_name)

    coordinator = UKBinCollectionDataUpdateCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info(LOG_PREFIX + "Successfully set up UK Bin Collection Data for council: %s", council_name)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of a UK Bin Collection Data config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        del hass.data[DOMAIN][entry.entry_id]
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle UK Bin Collection Data config entry options update."""
    await hass.config_entries.async_reload(entry.entry_id)


class UKBinCollectionDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching UK Bin Collection Data council data."""

    config_entry: ConfigEntry

    def __init__(
            self,
            hass: HomeAssistant,
    ) -> None:
        """Initialize global UK Bin Collection Data updater."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL
        )

        # Get config entry data
        data = self.config_entry.data
        _LOGGER.info(LOG_PREFIX + "Data: %s", data)
        # Get council args
        args = [
            data.get("council", ""),
            data.get("url", ""),
            *(f"--{key}={value}" for key, value in data.items() if
              key not in {"name", "council", "url", "skip_get_url"}),
        ]
        if "skip_get_url" in data:
            args.append("--skip_get_url")
        _LOGGER.info(LOG_PREFIX + "Args: %s", args)

        # Init UKBCD app with args
        self.ukbcd = UKBinCollectionApp()
        self.ukbcd.set_args(args)

    async def _async_update_data(self) -> object:
        """Fetch council data."""
        # Run UKBCD and get the JSON string
        json_string = await self.ukbcd.run()

        # Parse the JSON string into a Python dictionary
        council_data = json.loads(json_string)

        # Sort data by collection date
        council_data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        _LOGGER.info(LOG_PREFIX + "Council Data: %s", council_data)
        return council_data
