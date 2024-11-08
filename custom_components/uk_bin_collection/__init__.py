"""The UK Bin Collection integration."""

import asyncio
import logging
from datetime import timedelta
import json

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from datetime import datetime

from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOG_PREFIX, PLATFORMS
from uk_bin_collection.uk_bin_collection.collect_data import UKBinCollectionApp

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the UK Bin Collection component."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug(f"{LOG_PREFIX} async_setup called with config: {config}")
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries to new version."""
    if config_entry.version == 1:
        _LOGGER.info(
            f"{LOG_PREFIX} Migrating config entry {config_entry.entry_id} from version 1 to 2."
        )

        # Example: Add default update_interval if not present
        data = config_entry.data.copy()
        if "update_interval" not in data:
            data["update_interval"] = 12
            _LOGGER.debug(
                f"{LOG_PREFIX} 'update_interval' not found. Setting default to 12 hours."
            )
        else:
            _LOGGER.debug(
                f"{LOG_PREFIX} 'update_interval' found: {data['update_interval']} hours."
            )

        # Update the config entry with the new data
        hass.config_entries.async_update_entry(config_entry, data=data)

        _LOGGER.info(
            f"{LOG_PREFIX} Migration of config entry {config_entry.entry_id} to version 2 successful."
        )

    return True


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """Set up UK Bin Collection from a config entry."""
    _LOGGER.info(f"{LOG_PREFIX} Setting up UK Bin Collection.")

    name = config_entry.data.get("name")
    if not name:
        _LOGGER.error(f"{LOG_PREFIX} 'name' is missing in config entry.")
        raise ConfigEntryNotReady("Missing 'name' in configuration.")

    timeout = config_entry.data.get("timeout", 60)
    icon_color_mapping = config_entry.data.get("icon_color_mapping", "{}")
    update_interval_hours = config_entry.data.get("update_interval", 12)

    _LOGGER.debug(
        f"{LOG_PREFIX} Retrieved configuration: "
        f"name={name}, timeout={timeout}, "
        f"update_interval={update_interval_hours} hours, "
        f"icon_color_mapping={icon_color_mapping}"
    )

    # Validate 'timeout'
    try:
        timeout = int(timeout)
        if timeout < 10:
            _LOGGER.warning(
                f"{LOG_PREFIX} Timeout value {timeout} is less than 10. Setting to minimum of 10 seconds."
            )
            timeout = 10
    except (ValueError, TypeError):
        _LOGGER.warning(
            f"{LOG_PREFIX} Invalid timeout value: {timeout}. Using default 60 seconds."
        )
        timeout = 60

    # Validate 'update_interval_hours'
    try:
        update_interval_hours = int(update_interval_hours)
        if update_interval_hours < 1:
            _LOGGER.warning(
                f"{LOG_PREFIX} update_interval {update_interval_hours} is less than 1. Using default 12 hours."
            )
            update_interval_hours = 12
    except (ValueError, TypeError):
        _LOGGER.warning(
            f"{LOG_PREFIX} Invalid update_interval value: {update_interval_hours}. Using default 12 hours."
        )
        update_interval_hours = 12

    # Prepare arguments for UKBinCollectionApp
    args = build_ukbcd_args(config_entry.data)

    _LOGGER.debug(f"{LOG_PREFIX} UKBinCollectionApp args: {args}")

    # Initialize the UK Bin Collection Data application
    ukbcd = UKBinCollectionApp()
    ukbcd.set_args(args)
    _LOGGER.debug(f"{LOG_PREFIX} UKBinCollectionApp initialized and arguments set.")

    # Initialize the data coordinator
    coordinator = HouseholdBinCoordinator(
        hass,
        ukbcd,
        name,
        timeout=timeout,
        update_interval=timedelta(hours=update_interval_hours),
    )

    _LOGGER.debug(
        f"{LOG_PREFIX} HouseholdBinCoordinator initialized with update_interval={update_interval_hours} hours."
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as e:
        _LOGGER.error(f"{LOG_PREFIX} Unable to fetch initial data: {e}")
        raise ConfigEntryNotReady from e

    _LOGGER.info(f"{LOG_PREFIX} Initial data fetched successfully.")

    # Store the coordinator in Home Assistant's data
    hass.data[DOMAIN][config_entry.entry_id] = {"coordinator": coordinator}
    _LOGGER.debug(
        f"{LOG_PREFIX} Coordinator stored in hass.data under entry_id={config_entry.entry_id}."
    )

    # Forward the setup to all platforms (sensor and calendar)
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    )
    _LOGGER.debug(f"{LOG_PREFIX} Setup forwarded to platforms: {PLATFORMS}.")

    return True


async def async_unload_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """Unload a config entry."""
    _LOGGER.info(f"{LOG_PREFIX} Unloading config entry {config_entry.entry_id}.")
    unload_ok = True

    for platform in PLATFORMS:
        platform_unload_ok = await hass.config_entries.async_forward_entry_unload(
            config_entry, platform
        )
        if not platform_unload_ok:
            _LOGGER.warning(
                f"{LOG_PREFIX} Failed to unload '{platform}' platform for entry_id={config_entry.entry_id}."
            )
            unload_ok = False
        else:
            _LOGGER.debug(
                f"{LOG_PREFIX} Successfully unloaded '{platform}' platform for entry_id={config_entry.entry_id}."
            )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
        _LOGGER.debug(
            f"{LOG_PREFIX} Unloaded and removed coordinator for entry_id={config_entry.entry_id}."
        )
    else:
        _LOGGER.warning(
            f"{LOG_PREFIX} One or more platforms failed to unload for entry_id={config_entry.entry_id}."
        )

    return unload_ok


def build_ukbcd_args(config_data: dict) -> list:
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
        "update_interval",
    }

    args = [config_data.get("council", ""), config_data.get("url", "")]

    # Add other arguments
    for key, value in config_data.items():
        if key in excluded_keys:
            continue
        if key == "web_driver":
            value = value.rstrip("/")
        args.append(f"--{key}={value}")

    _LOGGER.debug(f"{LOG_PREFIX} Built UKBinCollectionApp arguments: {args}")
    return args


class HouseholdBinCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching and updating UK Bin Collection data."""

    def __init__(
        self,
        hass: HomeAssistant,
        ukbcd: UKBinCollectionApp,
        name: str,
        timeout: int = 60,
        update_interval: timedelta = timedelta(hours=12),
    ) -> None:
        """Initialize the data coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="UK Bin Collection Data",
            update_interval=update_interval,
        )
        self.ukbcd = ukbcd
        self.name = name
        self.timeout = timeout

        _LOGGER.debug(
            f"{LOG_PREFIX} DataUpdateCoordinator initialized with update_interval={update_interval}."
        )

    async def _async_update_data(self) -> dict:
        """Fetch and process the latest bin collection data."""
        _LOGGER.debug(
            f"{LOG_PREFIX} Starting data fetch with timeout={self.timeout} seconds."
        )
        _LOGGER.info(f"{LOG_PREFIX} Fetching latest bin collection data.")
        try:
            data = await asyncio.wait_for(
                self.hass.async_add_executor_job(self.ukbcd.run),
                timeout=self.timeout,
            )
            _LOGGER.debug(f"{LOG_PREFIX} Data fetched: {data}")
            parsed_data = json.loads(data)
            _LOGGER.debug(f"{LOG_PREFIX} Parsed data: {parsed_data}")
            processed_data = self.process_bin_data(parsed_data)
            _LOGGER.debug(f"{LOG_PREFIX} Processed data: {processed_data}")
            _LOGGER.info(f"{LOG_PREFIX} Bin collection data updated successfully.")
            return processed_data
        except asyncio.TimeoutError as exc:
            _LOGGER.error(f"{LOG_PREFIX} Timeout while updating data: {exc}")
            raise UpdateFailed(f"Timeout while updating data: {exc}") from exc
        except json.JSONDecodeError as exc:
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
                _LOGGER.debug(
                    f"{LOG_PREFIX} Updated next collection for '{bin_type}' to {collection_date}."
                )

        _LOGGER.debug(f"{LOG_PREFIX} Next Collection Dates: {next_collection_dates}")
        return next_collection_dates
