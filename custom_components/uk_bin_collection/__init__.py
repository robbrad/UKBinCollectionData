import json
from datetime import datetime
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

# Make sure the 'uk_bin_collection' library is installed for this import to work
from uk_bin_collection.uk_bin_collection import collect_data
from .const import DOMAIN, _LOGGER, LOG_PREFIX, PLATFORMS


def update(args: dict) -> object:
    """Retrieve council data."""
    # Get the JSON string from collect_data(args)
    json_string = collect_data.main(args)

    # Parse the JSON string into a Python dictionary
    council_data = json.loads(json_string)

    # Sort by collection date
    council_data["bins"].sort(
        key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
    )

    return council_data


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UK Bin Collection Data using UI."""
    hass.data.setdefault(DOMAIN, {})
    data = entry.data
    _LOGGER.info(LOG_PREFIX + "Data Supplied: %s", data)
    council_name = data.get("council", "unknown council")
    _LOGGER.info(LOG_PREFIX + "Setting up UK Bin Collection Data for council: %s", council_name)

    args = [
        data.get("council", ""),
        data.get("url", ""),
        *(f"--{key}={value}" for key, value in data.items() if key not in {"name", "council", "url", "skip_get_url"}),
    ]
    if "skip_get_url" in data:
        args.append("--skip_get_url")

    async def async_update() -> object:
        try:
            _LOGGER.debug(LOG_PREFIX + "Collecting data for council: %s", council_name)
            return await hass.async_add_executor_job(update, args)
        except Exception as ex:
            _LOGGER.error(LOG_PREFIX + "Failed to collect data for council: %s", council_name, exc_info=True)
            raise UpdateFailed("Unable to retrieve data") from ex

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update,
        update_interval=timedelta(hours=24)
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN] = coordinator

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info(LOG_PREFIX + "Successfully set up UK Bin Collection Data for council: %s", council_name)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        del hass.data[DOMAIN]
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
