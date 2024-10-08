from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import logging

_LOGGER = logging.getLogger(__name__)

from .const import DOMAIN, LOG_PREFIX, PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UK Bin Collection Data from a config entry."""
    _LOGGER.info(LOG_PREFIX + "Data Supplied: %s", entry.data)
    council_name = entry.data.get("council", "unknown council")
    _LOGGER.info(
        LOG_PREFIX + "Setting up UK Bin Collection Data for council: %s", council_name
    )

    hass.data.setdefault(DOMAIN, {})

    if entry.unique_id is None:
        name = entry.data["name"]
        hass.config_entries.async_update_entry(entry, unique_id=f"{name}")

    _LOGGER.info(LOG_PREFIX + "Config entry data: %s", entry.data)

    async def _async_finish_startup(_):
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    hass.async_create_task(_async_finish_startup(None))

    _LOGGER.info(
        LOG_PREFIX + "Successfully set up UK Bin Collection Data for council: %s",
        council_name,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
