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

from .const import DOMAIN, LOG_PREFIX, PLATFORMS, EXCLUDED_ARG_KEYS
from uk_bin_collection.uk_bin_collection.collect_data import UKBinCollectionApp


from homeassistant.helpers import config_validation as cv

PLATFORM_SCHEMA = cv.platform_only_config_schema

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the UK Bin Collection component."""
    _LOGGER.debug(f"{LOG_PREFIX} async_setup called with config: {config}")
    try:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.debug(f"{LOG_PREFIX} hass.data[DOMAIN] initialized: {hass.data[DOMAIN]}")

        async def handle_manual_refresh(call):
            """Refresh all bin sensors for a given config entry."""
            _LOGGER.debug(f"{LOG_PREFIX} manual_refresh service called with data: {call.data}")
            entry_id = call.data.get("entry_id")

            if not entry_id:
                _LOGGER.error(
                    "[UKBinCollection] No 'entry_id' was passed to uk_bin_collection.manual_refresh service."
                )
                return

            if entry_id not in hass.data[DOMAIN]:
                _LOGGER.error("[UKBinCollection] No config entry found for entry_id: %s", entry_id)
                return

            coordinator = hass.data[DOMAIN][entry_id].get("coordinator")
            if not coordinator:
                _LOGGER.error("[UKBinCollection] Coordinator is missing for entry_id: %s", entry_id)
                return

            _LOGGER.debug("[UKBinCollection] About to request a manual refresh via coordinator")
            await coordinator.async_request_refresh()
            _LOGGER.debug("[UKBinCollection] Manual refresh completed")

        # Register a service named `uk_bin_collection.manual_refresh`
        _LOGGER.debug("[UKBinCollection] Registering manual_refresh service")
        hass.services.async_register(
            DOMAIN,
            "manual_refresh",  # The service name
            handle_manual_refresh
        )
        _LOGGER.debug("[UKBinCollection] manual_refresh service registered successfully")

        _LOGGER.info("[UKBinCollection] async_setup completed without errors.")
        return True

    except Exception as exc:
        _LOGGER.exception("%s Unexpected error in async_setup: %s", LOG_PREFIX, exc)
        return False


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries to new version."""
    try:
        _LOGGER.debug(f"{LOG_PREFIX} async_migrate_entry called for entry_id={config_entry.entry_id}, version={config_entry.version}")

        if config_entry.version == 1:
            _LOGGER.info(
                f"{LOG_PREFIX} Migrating config entry {config_entry.entry_id} from version 1 to 2."
            )

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

            hass.config_entries.async_update_entry(config_entry, data=data)

            _LOGGER.info(
                f"{LOG_PREFIX} Migration of config entry {config_entry.entry_id} to version 2 successful."
            )

        else:
            _LOGGER.debug(f"{LOG_PREFIX} No migration needed for entry_id={config_entry.entry_id}")

        return True

    except Exception as exc:
        _LOGGER.exception("%s Unexpected error during async_migrate_entry: %s", LOG_PREFIX, exc)
        return False


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up UK Bin Collection from a config entry."""
    _LOGGER.info(f"{LOG_PREFIX} async_setup_entry called for entry_id={config_entry.entry_id}")

    try:
        name = config_entry.data.get("name")
        if not name:
            _LOGGER.error(f"{LOG_PREFIX} 'name' is missing in config entry.")
            raise ConfigEntryNotReady("Missing 'name' in configuration.")

        timeout = config_entry.data.get("timeout", 60)
        manual_refresh = config_entry.data.get("manual_refresh_only", False)
        icon_color_mapping = config_entry.data.get("icon_color_mapping", "{}")
        update_interval_hours = config_entry.data.get("update_interval", 12)

        _LOGGER.debug(
            f"{LOG_PREFIX} Retrieved configuration: "
            f"name={name}, timeout={timeout}, "
            f"manual_refresh_only={manual_refresh}, "
            f"update_interval={update_interval_hours} hours, "
            f"icon_color_mapping={icon_color_mapping}"
        )

        # Validate 'timeout'
        try:
            timeout = int(timeout)
            if timeout < 10:
                _LOGGER.warning(
                    f"{LOG_PREFIX} Timeout value {timeout} is less than 10. Setting to 10 seconds."
                )
                timeout = 10
        except (ValueError, TypeError):
            _LOGGER.warning(
                f"{LOG_PREFIX} Invalid timeout value: {timeout}. Using default 60 seconds."
            )
            timeout = 60

        # Decide update interval based on manual_refresh
        if manual_refresh:
            try:
                update_interval_hours = int(update_interval_hours)
                if update_interval_hours < 1:
                    update_interval_hours = 12
            except (ValueError, TypeError):
                update_interval_hours = 12
            update_interval = timedelta(hours=update_interval_hours)
            _LOGGER.info(
                "%s Automatic refresh every %s hour(s).",
                LOG_PREFIX,
                update_interval_hours,
            )
        else:
            update_interval = None
            _LOGGER.info("%s Manual refresh only: no automatic updates scheduled.", LOG_PREFIX)

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
            update_interval=update_interval,
        )

        _LOGGER.debug(
            f"{LOG_PREFIX} HouseholdBinCoordinator initialized with update_interval={update_interval}."
        )

        # Perform first refresh
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.info(f"{LOG_PREFIX} Initial data fetched successfully for entry_id={config_entry.entry_id}")

        # Store the coordinator in Home Assistant's data
        hass.data[DOMAIN][config_entry.entry_id] = {"coordinator": coordinator}
        _LOGGER.debug(
            f"{LOG_PREFIX} Coordinator stored in hass.data under entry_id={config_entry.entry_id}"
        )

        # Forward the setup to all platforms (sensor and calendar)
        _LOGGER.debug(f"{LOG_PREFIX} Forwarding setup to platforms: {PLATFORMS}")
        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

        _LOGGER.info(f"{LOG_PREFIX} async_setup_entry finished for entry_id={config_entry.entry_id}")
        return True

    except UpdateFailed as e:
        _LOGGER.error(f"{LOG_PREFIX} Unable to fetch initial data: {e}")
        raise ConfigEntryNotReady from e

    except Exception as exc:
        _LOGGER.exception("%s Unexpected error in async_setup_entry: %s", LOG_PREFIX, exc)
        raise ConfigEntryNotReady from exc


async def async_unload_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """Unload a config entry."""
    _LOGGER.info(f"{LOG_PREFIX} Unloading config entry {config_entry.entry_id}")
    unload_ok = True

    try:
        for platform in PLATFORMS:
            platform_unload_ok = await hass.config_entries.async_forward_entry_unload(
                config_entry, platform
            )
            if not platform_unload_ok:
                _LOGGER.warning(
                    f"{LOG_PREFIX} Failed to unload '{platform}' platform for entry_id={config_entry.entry_id}"
                )
                unload_ok = False
            else:
                _LOGGER.debug(
                    f"{LOG_PREFIX} Successfully unloaded '{platform}' for entry_id={config_entry.entry_id}"
                )

        if unload_ok:
            hass.data[DOMAIN].pop(config_entry.entry_id, None)
            _LOGGER.debug(
                f"{LOG_PREFIX} Removed coordinator for entry_id={config_entry.entry_id}"
            )
        else:
            _LOGGER.warning(
                f"{LOG_PREFIX} One or more platforms failed to unload for entry_id={config_entry.entry_id}"
            )

    except Exception as exc:
        _LOGGER.exception("%s Unexpected error in async_unload_entry: %s", LOG_PREFIX, exc)
        unload_ok = False

    return unload_ok


def build_ukbcd_args(config_data: dict) -> list:
    """Build the argument list for UKBinCollectionApp from config data."""
    _LOGGER.debug(f"{LOG_PREFIX} build_ukbcd_args called with config_data={config_data}")
    args = [config_data.get("council", ""), config_data.get("url", "")]

    # Add other arguments
    for key, value in config_data.items():
        if key in EXCLUDED_ARG_KEYS:
            _LOGGER.debug(f"{LOG_PREFIX} Skipping excluded key: {key}")
            continue
        if key == "web_driver" and value is not None:
            value = value.rstrip("/")
        arg_str = f"--{key}={value}"
        _LOGGER.debug(f"{LOG_PREFIX} Adding argument: {arg_str}")
        args.append(arg_str)

    _LOGGER.debug(f"{LOG_PREFIX} Final arguments list: {args}")
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

        self._last_good_data = {}

        _LOGGER.debug(
            f"{LOG_PREFIX} HouseholdBinCoordinator __init__: name={name}, timeout={timeout}, update_interval={update_interval}"
        )

    async def _async_update_data(self) -> dict:
        """Fetch and process the latest bin collection data."""
        _LOGGER.debug(f"{LOG_PREFIX} _async_update_data called.")
        _LOGGER.info(f"{LOG_PREFIX} Fetching latest bin collection data with timeout={self.timeout}")

        try:
            data = await asyncio.wait_for(
                self.hass.async_add_executor_job(self.ukbcd.run),
                timeout=self.timeout,
            )
            _LOGGER.debug(f"{LOG_PREFIX} Raw data fetched from ukbcd.run(): {data}")

            parsed_data = json.loads(data)
            _LOGGER.debug(f"{LOG_PREFIX} JSON parsed data: {parsed_data}")

            processed_data = self.process_bin_data(parsed_data)

            if not processed_data:
                _LOGGER.warning(f"{LOG_PREFIX} No bin data found. Using last known good data.")
                if self._last_good_data:
                    return self._last_good_data
                else:
                    _LOGGER.warning(f"{LOG_PREFIX} No previous data to fall back to.")
                    return {}

            self._last_good_data = processed_data
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
        _LOGGER.debug(f"{LOG_PREFIX} process_bin_data called with data={data}")

        current_date = dt_util.now().date()
        next_collection_dates = {}

        bins = data.get("bins", [])
        _LOGGER.debug(f"{LOG_PREFIX} Bins found: {bins}")
        for bin_data in bins:
            bin_type = bin_data.get("type")
            collection_date_str = bin_data.get("collectionDate")
            _LOGGER.debug(f"{LOG_PREFIX} Processing bin_data={bin_data}")

            if not bin_type or not collection_date_str:
                _LOGGER.warning(
                    f"{LOG_PREFIX} Missing 'type' or 'collectionDate' in bin data: {bin_data}"
                )
                continue

            try:
                collection_date = datetime.strptime(collection_date_str, "%d/%m/%Y").date()
            except (ValueError, TypeError) as exc:
                _LOGGER.warning(
                    f"{LOG_PREFIX} Invalid date format '{collection_date_str}' for bin type '{bin_type}'. Error: {exc}"
                )
                continue

            existing_date = next_collection_dates.get(bin_type)
            if collection_date >= current_date and (
                not existing_date or collection_date < existing_date
            ):
                next_collection_dates[bin_type] = collection_date
                _LOGGER.debug(
                    f"{LOG_PREFIX} Updated next collection for '{bin_type}' to {collection_date}"
                )

        _LOGGER.debug(f"{LOG_PREFIX} Final next_collection_dates={next_collection_dates}")
        return next_collection_dates
