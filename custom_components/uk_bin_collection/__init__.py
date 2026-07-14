"""The UK Bin Collection integration."""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from uk_bin_collection.uk_bin_collection.collect_data import UKBinCollectionApp

try:
    from uk_bin_collection.uk_bin_collection.exceptions import (
        AddressMismatchError,
        BrowserUnavailableError,
        ConfigurationError,
        DependencyError,
        DependencyShadowingError,
        MissingDependencyError,
        SiteChanged,
        UKBinCollectionError,
        UpstreamAccessDenied,
    )
except ImportError:  # Compatibility with a core package predating typed errors.

    class UKBinCollectionError(Exception):
        """Fallback base error used until the matching core package is installed."""

    class ConfigurationError(UKBinCollectionError):
        """Fallback invalid-configuration error."""

    class DependencyError(UKBinCollectionError):
        """Fallback used until the matching core package is installed."""

    class DependencyShadowingError(DependencyError):
        """Fallback dependency-shadowing error."""

    class MissingDependencyError(DependencyError):
        """Fallback missing-dependency error."""

    class BrowserUnavailableError(UKBinCollectionError):
        """Fallback browser-unavailable error."""

    class AddressMismatchError(UKBinCollectionError):
        """Fallback address-mismatch error."""

    class UpstreamAccessDenied(UKBinCollectionError):
        """Fallback upstream-access error."""

    class SiteChanged(UKBinCollectionError):
        """Fallback site-change error."""


from .const import (
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    LOG_PREFIX,
    PLATFORMS,
    SOUTH_KESTEVEN_COUNCIL,
    SOUTH_KESTEVEN_URL,
    STRING_ARGUMENTS,
    TRUE_FLAG_ARGUMENTS,
)

DEPENDENCY_ERRORS = (DependencyError,)

PLATFORM_SCHEMA = cv.platform_only_config_schema

_LOGGER = logging.getLogger(__name__)

_COLLECTOR_RUN_STATES = "_collector_run_states"

# The South Kesteven collector has its own 90-second wall-clock deadline and
# uses a remote-command timeout of up to 30 seconds while closing the browser.
# Keep HA's outer wait beyond both bounds so the collector normally terminates
# and releases its browser before HA reports a timeout. This is deliberately
# council-specific; other collectors retain the configured timeout contract.
_SOUTH_KESTEVEN_MIN_HA_TIMEOUT_SECONDS = 125


@dataclass(slots=True)
class _CollectorRunState:
    """Entry-scoped state shared by coordinators across setup retries/reloads."""

    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    active_run: asyncio.Future | None = None
    discard_when_idle: bool = False


def _collector_run_state(
    hass: HomeAssistant, entry_id: str | None
) -> _CollectorRunState:
    """Return durable in-flight state for one entry before its first refresh."""
    if not entry_id:
        return _CollectorRunState()

    domain_data = hass.data.setdefault(DOMAIN, {})
    run_states = domain_data.setdefault(_COLLECTOR_RUN_STATES, {})
    return run_states.setdefault(entry_id, _CollectorRunState())


def _release_collector_run_state(
    hass: HomeAssistant,
    entry_id: str | None,
    *,
    expected: _CollectorRunState | None = None,
) -> None:
    """Discard idle entry state, or defer cleanup until its executor finishes."""
    if not entry_id:
        return

    domain_data = hass.data.get(DOMAIN)
    if not isinstance(domain_data, dict):
        return
    run_states = domain_data.get(_COLLECTOR_RUN_STATES)
    if not isinstance(run_states, dict):
        return

    state = run_states.get(entry_id)
    if state is None:
        if not run_states:
            domain_data.pop(_COLLECTOR_RUN_STATES, None)
        return
    if expected is not None and state is not expected:
        return

    active_run = state.active_run
    if active_run is not None and not active_run.done():
        state.discard_when_idle = True
        return

    run_states.pop(entry_id, None)
    if not run_states:
        domain_data.pop(_COLLECTOR_RUN_STATES, None)


def _coerce_bool(value: Any, *, default: bool = False) -> bool:
    """Return a stable boolean for values saved by older config flows."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", ""}:
            return False
    return bool(value)


def _issue_id(kind: str, entry_id: str) -> str:
    """Return a stable Repairs issue id for an entry."""
    return f"{kind}_{entry_id}"


def _delete_issue_safely(hass: HomeAssistant, issue_id: str) -> None:
    """Clear a resolved Repairs issue without breaking a data refresh."""
    try:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
    except Exception:  # Repairs cleanup is best-effort and contains no user data.
        _LOGGER.debug(
            "%s Could not clear a resolved Repairs issue.",
            LOG_PREFIX,
        )


def _create_dependency_issue(
    hass: HomeAssistant, entry_id: str, exc: BaseException
) -> None:
    """Create an actionable Repairs issue without logging household data."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id("dependency", entry_id),
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="dependency_error",
        translation_placeholders={"details": str(exc)},
    )


def _missing_required_configuration(config_data: dict[str, Any]) -> list[str]:
    """Return required South Kesteven values absent from a migrated entry."""
    if config_data.get("council") != SOUTH_KESTEVEN_COUNCIL:
        return []

    missing = [
        field
        for field in ("postcode", "number")
        if not str(config_data.get(field, "")).strip()
    ]
    has_web_driver = bool(str(config_data.get("web_driver", "")).strip())
    has_local_browser = _coerce_bool(config_data.get("local_browser"))
    if not has_web_driver:
        missing.append("web_driver")
    if has_local_browser:
        missing.append("disable local_browser for this council")
    return missing


def _create_missing_configuration_issue(
    hass: HomeAssistant, entry_id: str, missing: list[str]
) -> None:
    """Tell the user to use the integration's reconfigure flow."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id("missing_configuration", entry_id),
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="missing_required_configuration",
        translation_placeholders={"fields": ", ".join(missing)},
    )


def _create_browser_issue(
    hass: HomeAssistant, entry_id: str, exc: BaseException
) -> None:
    """Create one stable, actionable issue for an unavailable WebDriver."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id("browser", entry_id),
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="browser_unavailable",
        translation_placeholders={"details": str(exc)},
    )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the UK Bin Collection component."""
    _LOGGER.debug("%s async_setup called.", LOG_PREFIX)
    try:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.debug("%s Integration runtime storage initialized.", LOG_PREFIX)

        async def handle_manual_refresh(call):
            """Refresh all bin sensors for a given config entry."""
            _LOGGER.debug("%s manual_refresh service called.", LOG_PREFIX)
            entry_id = call.data.get("entry_id")

            if not entry_id:
                _LOGGER.error(
                    "[UKBinCollection] No 'entry_id' was passed to uk_bin_collection.manual_refresh service."
                )
                return

            if entry_id not in hass.data[DOMAIN]:
                _LOGGER.error("[UKBinCollection] Requested config entry was not found")
                return

            coordinator = hass.data[DOMAIN][entry_id].get("coordinator")
            if not coordinator:
                _LOGGER.error(
                    "[UKBinCollection] Coordinator is missing for the requested entry"
                )
                return

            _LOGGER.debug(
                "[UKBinCollection] About to request a manual refresh via coordinator"
            )
            await coordinator.async_request_refresh()
            _LOGGER.debug("[UKBinCollection] Manual refresh completed")

        # Register a service named `uk_bin_collection.manual_refresh`
        _LOGGER.debug("[UKBinCollection] Registering manual_refresh service")
        hass.services.async_register(
            DOMAIN, "manual_refresh", handle_manual_refresh  # The service name
        )
        _LOGGER.debug(
            "[UKBinCollection] manual_refresh service registered successfully"
        )

        _LOGGER.info("[UKBinCollection] async_setup completed without errors.")
        return True

    except Exception as exc:
        _LOGGER.error(
            "%s Unexpected error in async_setup (%s).",
            LOG_PREFIX,
            type(exc).__name__,
        )
        return False


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate config entries sequentially to the current schema."""
    try:
        version = config_entry.version
        if version > CONFIG_ENTRY_VERSION:
            _LOGGER.error(
                "%s Config entry %s has unsupported future version %s",
                LOG_PREFIX,
                config_entry.entry_id,
                version,
            )
            return False

        if version == CONFIG_ENTRY_VERSION:
            return True

        data = dict(config_entry.data)

        if version < 2:
            data.setdefault("update_interval", 12)
            version = 2

        if version < 3:
            data.setdefault("manual_refresh_only", True)
            version = 3

        if version < 4:
            if data.get("update_interval") is None:
                data["update_interval"] = 12
            data["manual_refresh_only"] = _coerce_bool(
                data.get("manual_refresh_only"), default=True
            )
            data["headless"] = _coerce_bool(data.get("headless"), default=True)
            data["local_browser"] = _coerce_bool(data.get("local_browser"))
            data["skip_get_url"] = _coerce_bool(data.get("skip_get_url"))

            number_candidates = (
                data.get("number"),
                data.pop("house_number", None),
                data.pop("paon", None),
            )
            normalized_number = next(
                (
                    str(candidate).strip()
                    for candidate in number_candidates
                    if candidate is not None and str(candidate).strip()
                ),
                "",
            )
            if normalized_number:
                data["number"] = normalized_number
            else:
                data.pop("number", None)

            web_driver_candidates = (
                data.get("web_driver"),
                data.pop("selenium_url", None),
                data.pop("webdriver", None),
            )
            normalized_web_driver = next(
                (
                    str(candidate).strip().rstrip("/")
                    for candidate in web_driver_candidates
                    if candidate is not None and str(candidate).strip().rstrip("/")
                ),
                "",
            )
            if normalized_web_driver:
                data["web_driver"] = normalized_web_driver
            else:
                data.pop("web_driver", None)

            if data.get("council") == SOUTH_KESTEVEN_COUNCIL:
                data["url"] = SOUTH_KESTEVEN_URL
                data["skip_get_url"] = True
            version = 4

        hass.config_entries.async_update_entry(
            config_entry,
            data=data,
            version=CONFIG_ENTRY_VERSION,
        )
        _LOGGER.info(
            "%s Migrated config entry %s to version %s",
            LOG_PREFIX,
            config_entry.entry_id,
            CONFIG_ENTRY_VERSION,
        )

        return True

    except Exception as exc:
        _LOGGER.error(
            "%s Unexpected error during async_migrate_entry (%s).",
            LOG_PREFIX,
            type(exc).__name__,
        )
        return False


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up UK Bin Collection from a config entry."""
    _LOGGER.info(
        f"{LOG_PREFIX} async_setup_entry called for entry_id={config_entry.entry_id}"
    )

    try:
        name = config_entry.data.get("name")
        if not name:
            _LOGGER.error(f"{LOG_PREFIX} 'name' is missing in config entry.")
            raise ConfigEntryError(
                "Missing 'name' in configuration. Reconfigure this integration entry."
            )

        timeout = config_entry.data.get("timeout", 60)
        manual_refresh = _coerce_bool(
            config_entry.data.get("manual_refresh_only"), default=True
        )
        update_interval_hours = config_entry.data.get("update_interval", 12)

        _LOGGER.debug(
            "%s Retrieved non-sensitive scheduling configuration: "
            "timeout=%s, manual_refresh_only=%s, update_interval=%s hours",
            LOG_PREFIX,
            timeout,
            manual_refresh,
            update_interval_hours,
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

        if config_entry.data.get("council") == SOUTH_KESTEVEN_COUNCIL:
            timeout = max(timeout, _SOUTH_KESTEVEN_MIN_HA_TIMEOUT_SECONDS)

        # A true manual_refresh_only value must never schedule council requests.
        if manual_refresh:
            update_interval = None
            _LOGGER.info(
                "%s Manual refresh only: no automatic updates scheduled.", LOG_PREFIX
            )
        else:
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

        missing = _missing_required_configuration(config_entry.data)
        if missing:
            _create_missing_configuration_issue(hass, config_entry.entry_id, missing)
            raise ConfigEntryError(
                "Missing required configuration: "
                f"{', '.join(missing)}. Reconfigure this integration entry."
            )
        _delete_issue_safely(
            hass, _issue_id("missing_configuration", config_entry.entry_id)
        )

        # Prepare arguments for UKBinCollectionApp
        args = build_ukbcd_args(config_entry.data)
        _LOGGER.debug(
            "%s Built UKBinCollectionApp arguments for the configured council",
            LOG_PREFIX,
        )

        # Initialize the UK Bin Collection Data application
        ukbcd = UKBinCollectionApp()
        ukbcd.set_args(args)
        _LOGGER.debug(f"{LOG_PREFIX} UKBinCollectionApp initialized and arguments set.")

        # Initialize the data coordinator
        # This state must exist before the first refresh. Home Assistant may build
        # another coordinator after ConfigEntryNotReady while the executor thread
        # from the first attempt is still running.
        run_state = _collector_run_state(hass, config_entry.entry_id)
        coordinator = HouseholdBinCoordinator(
            hass,
            ukbcd,
            name,
            timeout=timeout,
            update_interval=update_interval,
            config_entry=config_entry,
            run_state=run_state,
        )

        _LOGGER.debug(
            f"{LOG_PREFIX} HouseholdBinCoordinator initialized with update_interval={update_interval}."
        )

        # Perform first refresh
        try:
            await coordinator.async_config_entry_first_refresh()
        except asyncio.CancelledError:
            _release_collector_run_state(
                hass, config_entry.entry_id, expected=run_state
            )
            raise
        except Exception:
            # Permanent setup failures must not leak idle per-entry state. If a
            # timed-out executor is still running, cleanup is deferred until its
            # completion callback observes that it is safe to remove.
            _release_collector_run_state(
                hass, config_entry.entry_id, expected=run_state
            )
            raise
        _delete_issue_safely(hass, _issue_id("dependency", config_entry.entry_id))
        _delete_issue_safely(
            hass, _issue_id("missing_configuration", config_entry.entry_id)
        )
        _delete_issue_safely(hass, _issue_id("browser", config_entry.entry_id))
        _LOGGER.info(
            f"{LOG_PREFIX} Initial data fetched successfully for entry_id={config_entry.entry_id}"
        )

        # Store the coordinator in Home Assistant's data
        hass.data[DOMAIN][config_entry.entry_id] = {"coordinator": coordinator}
        _LOGGER.debug(
            f"{LOG_PREFIX} Coordinator stored in hass.data under entry_id={config_entry.entry_id}"
        )

        # Forward the setup to all platforms (sensor and calendar)
        _LOGGER.debug(f"{LOG_PREFIX} Forwarding setup to platforms: {PLATFORMS}")
        try:
            await hass.config_entries.async_forward_entry_setups(
                config_entry, PLATFORMS
            )
        except asyncio.CancelledError:
            hass.data[DOMAIN].pop(config_entry.entry_id, None)
            _release_collector_run_state(
                hass, config_entry.entry_id, expected=run_state
            )
            raise
        except Exception:
            # Platform setup needs the coordinator in hass.data, but a failed
            # forward must not leave a setup-retry entry callable through the
            # manual-refresh service.
            hass.data[DOMAIN].pop(config_entry.entry_id, None)
            _release_collector_run_state(
                hass, config_entry.entry_id, expected=run_state
            )
            raise

        _LOGGER.info(
            f"{LOG_PREFIX} async_setup_entry finished for entry_id={config_entry.entry_id}"
        )
        return True

    except (ConfigEntryError, ConfigEntryNotReady):
        raise

    except DEPENDENCY_ERRORS as exc:
        _create_dependency_issue(hass, config_entry.entry_id, exc)
        raise ConfigEntryError(
            "A Python dependency could not be loaded safely. "
            "Open Repairs for the conflicting package path."
        ) from exc

    except UpdateFailed as exc:
        error_class = type(exc).__name__
        _LOGGER.error("%s Initial data fetch failed (%s).", LOG_PREFIX, error_class)
        raise ConfigEntryNotReady(
            f"Initial collection lookup failed ({error_class})."
        ) from None

    except Exception as exc:
        error_class = type(exc).__name__
        _LOGGER.error(
            "%s Unexpected error in async_setup_entry (%s).",
            LOG_PREFIX,
            error_class,
        )
        raise ConfigEntryNotReady(
            f"Unexpected integration setup error ({error_class})."
        ) from None


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info(f"{LOG_PREFIX} Unloading config entry {config_entry.entry_id}")

    try:
        unload_ok = await hass.config_entries.async_unload_platforms(
            config_entry, PLATFORMS
        )

        if unload_ok:
            hass.data[DOMAIN].pop(config_entry.entry_id, None)
            _release_collector_run_state(hass, config_entry.entry_id)
            _LOGGER.debug(
                f"{LOG_PREFIX} Removed coordinator for entry_id={config_entry.entry_id}"
            )
        else:
            _LOGGER.warning(
                f"{LOG_PREFIX} One or more platforms failed to unload for entry_id={config_entry.entry_id}"
            )

    except Exception as exc:
        _LOGGER.error(
            "%s Unexpected error in async_unload_entry (%s).",
            LOG_PREFIX,
            type(exc).__name__,
        )
        unload_ok = False

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Remove entry-scoped runtime state and Repairs issues."""
    domain_data = hass.data.get(DOMAIN)
    if isinstance(domain_data, dict):
        domain_data.pop(config_entry.entry_id, None)
    _release_collector_run_state(hass, config_entry.entry_id)
    for kind in ("dependency", "missing_configuration", "browser"):
        _delete_issue_safely(hass, _issue_id(kind, config_entry.entry_id))


def build_ukbcd_args(config_data: dict[str, Any]) -> list[str]:
    """Build arguments using only the core library's declared CLI contract."""
    council = config_data.get("original_parser") or config_data.get("council", "")
    url = config_data.get("url", "")
    args = [str(council).strip(), str(url).strip()]

    for key, option in STRING_ARGUMENTS.items():
        value = config_data.get(key)
        if value is None:
            continue
        normalized = str(value).strip()
        if not normalized:
            continue
        if key == "web_driver":
            normalized = normalized.rstrip("/")
        args.append(f"{option}={normalized}")

    for key, option in TRUE_FLAG_ARGUMENTS.items():
        if _coerce_bool(config_data.get(key)):
            args.append(option)

    if "headless" in config_data:
        args.append(
            "--headless"
            if _coerce_bool(config_data.get("headless"), default=True)
            else "--not-headless"
        )

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
        config_entry: ConfigEntry | None = None,
        config_entry_id: str | None = None,
        run_state: _CollectorRunState | None = None,
    ) -> None:
        """Initialize the data coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name="UK Bin Collection Data",
            update_interval=update_interval,
        )
        self.ukbcd = ukbcd
        self.name = name
        self.timeout = timeout
        self.config_entry_id = (
            config_entry.entry_id if config_entry is not None else config_entry_id
        )

        self._last_good_data = {}
        self._run_state = run_state or _collector_run_state(hass, self.config_entry_id)

        _LOGGER.debug(
            "%s HouseholdBinCoordinator initialized: timeout=%s, update_interval=%s",
            LOG_PREFIX,
            timeout,
            update_interval,
        )

    async def _async_update_data(self) -> dict:
        """Fetch and process the latest bin collection data."""
        _LOGGER.debug(f"{LOG_PREFIX} _async_update_data called.")
        _LOGGER.info(
            f"{LOG_PREFIX} Fetching latest bin collection data with timeout={self.timeout}"
        )

        try:
            async with self._run_state.lock:
                if (
                    self._run_state.active_run is not None
                    and not self._run_state.active_run.done()
                ):
                    raise UpdateFailed(
                        "The previous collector run is still finishing after its timeout."
                    )
                run_future = asyncio.ensure_future(
                    self.hass.async_add_executor_job(self.ukbcd.run)
                )
                # A new setup has legitimately reused this state after a prior
                # unload. Do not let the old run's deferred cleanup remove it.
                self._run_state.discard_when_idle = False
                self._run_state.active_run = run_future
                run_future.add_done_callback(self._clear_active_run)

            # Shield the executor future: cancelling the asyncio wait cannot stop a
            # running thread, and retaining it prevents a second overlapping scrape.
            data = await asyncio.wait_for(
                asyncio.shield(run_future),
                timeout=self.timeout,
            )
            parsed_data = json.loads(data)

            if self.config_entry_id:
                _delete_issue_safely(
                    self.hass, _issue_id("dependency", self.config_entry_id)
                )
                _delete_issue_safely(
                    self.hass, _issue_id("browser", self.config_entry_id)
                )

            processed_data = self.process_bin_data(parsed_data)

            if not processed_data:
                _LOGGER.warning(
                    f"{LOG_PREFIX} No bin data found. Using last known good data."
                )
                if self._last_good_data:
                    return self._last_good_data
                else:
                    _LOGGER.warning(f"{LOG_PREFIX} No previous data to fall back to.")
                    return {}

            self._last_good_data = processed_data
            _LOGGER.info(f"{LOG_PREFIX} Bin collection data updated successfully.")
            return processed_data

        except asyncio.TimeoutError:
            _LOGGER.error("%s Timeout while updating data.", LOG_PREFIX)
            raise UpdateFailed("Timeout while updating data.") from None
        except json.JSONDecodeError:
            _LOGGER.error("%s JSON decode error in collector output.", LOG_PREFIX)
            raise UpdateFailed("JSON decode error in collector output.") from None
        except DEPENDENCY_ERRORS as exc:
            if self.config_entry_id:
                _delete_issue_safely(
                    self.hass, _issue_id("browser", self.config_entry_id)
                )
                _create_dependency_issue(self.hass, self.config_entry_id, exc)
            raise ConfigEntryError(
                "A Python dependency is missing or shadowed. "
                "Open Home Assistant Repairs for remediation details."
            ) from exc
        except BrowserUnavailableError as exc:
            if self.config_entry_id:
                _delete_issue_safely(
                    self.hass, _issue_id("dependency", self.config_entry_id)
                )
                _create_browser_issue(self.hass, self.config_entry_id, exc)
            _LOGGER.warning("%s Selenium WebDriver is unavailable.", LOG_PREFIX)
            raise UpdateFailed(
                "Selenium WebDriver is unavailable. Check Home Assistant Repairs "
                "and the configured browser endpoint."
            ) from exc
        except (ConfigurationError, AddressMismatchError) as exc:
            if self.config_entry_id and isinstance(exc, AddressMismatchError):
                _delete_issue_safely(
                    self.hass, _issue_id("dependency", self.config_entry_id)
                )
                _delete_issue_safely(
                    self.hass, _issue_id("browser", self.config_entry_id)
                )
            _LOGGER.warning(
                "%s Council lookup configuration requires user action: %s",
                LOG_PREFIX,
                type(exc).__name__,
            )
            raise ConfigEntryError(
                "The configured address or council settings need to be corrected. "
                "Reconfigure this integration entry."
            ) from exc
        except UpstreamAccessDenied as exc:
            if self.config_entry_id:
                _delete_issue_safely(
                    self.hass, _issue_id("dependency", self.config_entry_id)
                )
                _delete_issue_safely(
                    self.hass, _issue_id("browser", self.config_entry_id)
                )
            _LOGGER.warning("%s Council browser access was denied.", LOG_PREFIX)
            raise UpdateFailed(
                "The council denied browser access to its collection checker."
            ) from exc
        except SiteChanged as exc:
            if self.config_entry_id:
                _delete_issue_safely(
                    self.hass, _issue_id("dependency", self.config_entry_id)
                )
                _delete_issue_safely(
                    self.hass, _issue_id("browser", self.config_entry_id)
                )
            _LOGGER.warning("%s Council website structure changed.", LOG_PREFIX)
            raise UpdateFailed(
                "The council collection checker no longer matches its supported layout."
            ) from exc
        except UKBinCollectionError as exc:
            _LOGGER.warning(
                "%s Expected council lookup failure: %s",
                LOG_PREFIX,
                type(exc).__name__,
            )
            raise UpdateFailed(
                "The council lookup failed with a recognized collector error."
            ) from exc
        except UpdateFailed:
            raise
        except Exception as exc:
            error_class = type(exc).__name__
            _LOGGER.error(
                "%s Unexpected coordinator error (%s).",
                LOG_PREFIX,
                error_class,
            )
            raise UpdateFailed(f"Unexpected collector error ({error_class}).") from None

    def _clear_active_run(self, completed: asyncio.Future) -> None:
        """Release the in-flight marker and consume a late executor exception."""
        if self._run_state.active_run is completed:
            self._run_state.active_run = None
        if not completed.cancelled():
            try:
                completed.exception()
            except Exception:
                # The next scheduled refresh reports its own fresh outcome; do not
                # emit late thread exception details that may contain address data.
                pass
        if self._run_state.discard_when_idle:
            _release_collector_run_state(
                self.hass,
                self.config_entry_id,
                expected=self._run_state,
            )

    @property
    def _active_run(self) -> asyncio.Future | None:
        """Expose the shared in-flight future for diagnostics and tests."""
        return self._run_state.active_run

    @staticmethod
    def process_bin_data(data: dict) -> dict:
        """Process raw data to determine the next collection dates."""
        _LOGGER.debug("%s Processing normalized collection data.", LOG_PREFIX)

        current_date = dt_util.now().date()
        next_collection_dates = {}

        bins = data.get("bins", [])
        _LOGGER.debug("%s Collection rows received: %s", LOG_PREFIX, len(bins))
        for bin_data in bins:
            bin_type = bin_data.get("type")
            collection_date_str = bin_data.get("collectionDate")
            if not bin_type or not collection_date_str:
                _LOGGER.warning(
                    "%s Collection row is missing a type or date.", LOG_PREFIX
                )
                continue

            try:
                collection_date = datetime.strptime(
                    collection_date_str, "%d/%m/%Y"
                ).date()
            except (ValueError, TypeError) as exc:
                _LOGGER.warning(
                    "%s A collection row has an invalid date format.", LOG_PREFIX
                )
                continue

            if (
                collection_date < current_date
                and current_date.month == 12
                and collection_date.month == 1
            ):
                collection_date = collection_date.replace(year=current_date.year + 1)
                _LOGGER.debug(
                    "%s Corrected a year-boundary collection date.", LOG_PREFIX
                )

            existing_date = next_collection_dates.get(bin_type)
            if collection_date >= current_date and (
                not existing_date or collection_date < existing_date
            ):
                next_collection_dates[bin_type] = collection_date
                _LOGGER.debug("%s Updated a normalized collection date.", LOG_PREFIX)

        _LOGGER.debug(
            "%s Normalized collection types: %s",
            LOG_PREFIX,
            len(next_collection_dates),
        )
        return next_collection_dates
