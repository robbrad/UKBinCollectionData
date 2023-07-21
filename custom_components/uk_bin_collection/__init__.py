import asyncio
import json
import logging

from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorEntity

# Make sure the 'uk_bin_collection' library is installed for this import to work
from uk_bin_collection.uk_bin_collection import collect_data

DOMAIN = "uk_bin_collection"

_LOGGER = logging.getLogger(__name__)
LOG_PREFIX = "[UKBinCollection] "

async def async_setup(hass, config):
    """Set up the UK Bin Collection component."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info(LOG_PREFIX + "UK Bin Collection component initialized")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UK Bin Collection config entry."""
    data = entry.data
    _LOGGER.info(LOG_PREFIX + "Data Supplied: %s", data)
    council_name = data.get("council", "unknown council")
    _LOGGER.info(LOG_PREFIX + "Setting up UK Bin Collection for council: %s", council_name)

    args = [
        data.get("council", ""),
        data.get("url", ""),
        *(f"-{key[0]}={value}" for key, value in data.items() if key not in {"council", "url"}),
    ]

    try:
        _LOGGER.debug(LOG_PREFIX + "Collecting data for council: %s", council_name)
        # Get the JSON string from collect_data(args)
        json_string = await collect_data.main(args)

        # Parse the JSON string into a Python dictionary
        council_data = json.loads(json_string)
        _LOGGER.debug(LOG_PREFIX + "Data collected for council: %s", council_name)
    except Exception as err:
        _LOGGER.error(LOG_PREFIX + "Failed to collect data for council: %s", council_name, exc_info=True)
        raise ConfigEntryNotReady from err

    hass.data[DOMAIN][entry.entry_id] = council_data

    # Set up the sensor entity to display the next bin collection date
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, SENSOR_DOMAIN)
    )

    _LOGGER.info(LOG_PREFIX + "Successfully set up UK Bin Collection for council: %s", council_name)
    return True
