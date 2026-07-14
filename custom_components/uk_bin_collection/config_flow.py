import asyncio
import json
import logging
import shutil
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urlsplit

import aiohttp
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    BROWSER_BINARIES,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    INPUT_JSON_URL,
    LOG_PREFIX,
    SELENIUM_SERVER_URLS,
    SOUTH_KESTEVEN_COUNCIL,
)

_LOGGER = logging.getLogger(__name__)

COUNCIL_SCOPED_FIELDS = {
    "url",
    "postcode",
    "number",
    "paon",
    "house_number",
    "uprn",
    "usrn",
    "web_driver",
    "headless",
    "local_browser",
    "skip_get_url",
    "user_agent",
    "artifact_dir",
}


def normalize_council_registry(
    original_data: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Normalize real councils and aliases through one shared registry path."""
    normalized_data: Dict[str, Dict[str, Any]] = {}
    for key, raw_value in original_data.items():
        value = dict(raw_value)
        if "paon" in value and "house_number" not in value:
            value["house_number"] = value["paon"]
        normalized_data[key] = value
        for alias in value.get("supported_councils", []):
            alias_data = dict(value)
            alias_data["original_parser"] = key
            alias_data["wiki_name"] = (
                f"{alias.replace('Council', ' Council')} (via Google Calendar)"
            )
            normalized_data[alias] = alias_data
    return dict(sorted(normalized_data.items()))


async def async_fetch_council_registry() -> Dict[str, Dict[str, Any]]:
    """Fetch and normalize the registry used by every config-entry flow."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(INPUT_JSON_URL, timeout=15) as response:
                response.raise_for_status()
                return normalize_council_registry(json.loads(await response.text()))
    except Exception as exc:
        _LOGGER.error("Error fetching council data (%s).", type(exc).__name__)
        return {}


def apply_registry_metadata(
    data: Dict[str, Any], council_key: str, council_info: Mapping[str, Any]
) -> None:
    """Apply non-secret parser metadata consistently to persisted data."""
    data["council"] = council_key
    original_parser = council_info.get("original_parser")
    if original_parser:
        data["original_parser"] = original_parser
    else:
        data.pop("original_parser", None)

    if council_info.get("skip_get_url", False):
        data["skip_get_url"] = True
    else:
        data.pop("skip_get_url", None)
    if data.get("skip_get_url") and not council_info.get(
        "custom_component_show_url_field"
    ):
        data["url"] = council_info.get("url", data.get("url", ""))


def merge_council_data(
    existing_data: Mapping[str, Any],
    user_input: Mapping[str, Any],
    *,
    previous_council: str,
    selected_council: str,
) -> Dict[str, Any]:
    """Merge a form without carrying household data to a different council."""
    data = dict(existing_data)
    if previous_council != selected_council:
        for field in COUNCIL_SCOPED_FIELDS:
            data.pop(field, None)
    data.update(user_input)
    return data


def validate_council_input(
    council_info: Mapping[str, Any], data: Mapping[str, Any]
) -> Dict[str, str]:
    """Validate registry-required fields, including browser selection."""
    errors: Dict[str, str] = {}
    required_fields = []
    if not council_info.get("skip_get_url", False) or council_info.get(
        "custom_component_show_url_field"
    ):
        required_fields.append("url")
    for registry_key, form_key in (
        ("uprn", "uprn"),
        ("postcode", "postcode"),
        ("house_number", "number"),
        ("usrn", "usrn"),
    ):
        if registry_key in council_info:
            required_fields.append(form_key)

    for field in required_fields:
        if not str(data.get(field, "")).strip():
            errors[field] = "required"

    if "web_driver" in council_info:
        local_browser = bool(data.get("local_browser", False))
        web_driver = str(data.get("web_driver", "")).strip()
        if data.get("council") == SOUTH_KESTEVEN_COUNCIL and (
            local_browser or not web_driver
        ):
            errors["web_driver"] = "remote_browser_required"
        elif not local_browser and not web_driver:
            errors["web_driver"] = "browser_required"
        elif local_browser and web_driver:
            errors["web_driver"] = "browser_conflict"
        elif web_driver and not _is_valid_webdriver_url(web_driver):
            errors["web_driver"] = "invalid_webdriver_url"
    return errors


def _is_valid_webdriver_url(value: str) -> bool:
    """Accept only an HTTP(S) endpoint with a syntactically valid host and port."""
    normalized = value.strip()
    try:
        parsed = urlsplit(normalized)
        hostname = parsed.hostname
        parsed.port
    except (TypeError, ValueError):
        return False
    return bool(
        parsed.scheme.casefold() in {"http", "https"}
        and hostname
        and not any(character.isspace() for character in normalized)
    )


def add_registry_fields(
    fields: Dict[Any, Any],
    council_info: Mapping[str, Any],
    existing_data: Mapping[str, Any],
) -> None:
    """Add registry-defined fields to setup, options, and reconfigure forms."""

    def required(name: str, validator: Any) -> None:
        if name in existing_data:
            fields[vol.Required(name, default=existing_data[name])] = validator
        else:
            fields[vol.Required(name)] = validator

    if not council_info.get("skip_get_url", False) or council_info.get(
        "custom_component_show_url_field"
    ):
        required("url", cv.string)
    if "uprn" in council_info:
        required("uprn", cv.string)
    if "postcode" in council_info:
        required("postcode", cv.string)
    if "house_number" in council_info:
        required("number", cv.string)
    if "usrn" in council_info:
        required("usrn", cv.string)
    if "web_driver" in council_info:
        fields[
            vol.Optional("web_driver", default=existing_data.get("web_driver", ""))
        ] = cv.string
        fields[
            vol.Optional("headless", default=existing_data.get("headless", True))
        ] = bool
        fields[
            vol.Optional(
                "local_browser", default=existing_data.get("local_browser", False)
            )
        ] = bool
        fields[
            vol.Optional("user_agent", default=existing_data.get("user_agent", ""))
        ] = cv.string


class UkBinCollectionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UkBinCollection."""

    VERSION = CONFIG_ENTRY_VERSION

    def __init__(self):
        self.councils_data: Optional[Dict[str, Any]] = None
        self.data: Dict[str, Any] = {}
        self.council_names: list = []
        self.council_options: list = []
        self.selenium_checked: bool = False
        self.selenium_available: bool = False
        self.selenium_results: list = []
        self.chromium_checked: bool = False
        self.chromium_installed: bool = False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return an options flow; Home Assistant supplies its config entry."""
        del config_entry
        return UkBinCollectionOptionsFlowHandler()

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle the initial step."""
        errors = {}

        if self.councils_data is None:
            self.councils_data = await self.get_councils_json()
            if not self.councils_data:
                _LOGGER.error("Council data is unavailable.")
                return self.async_abort(reason="council_data_unavailable")

            self.council_names = list(self.councils_data.keys())
            self.council_options = [
                self.councils_data[name]["wiki_name"] for name in self.council_names
            ]
            _LOGGER.debug("Loaded council data: %s", self.council_names)

        if user_input is not None:
            _LOGGER.debug("User input fields received: %s", sorted(user_input))
            # Validate user input
            if not user_input.get("name"):
                errors["name"] = "name"
            if not user_input.get("council"):
                errors["council"] = "council"

            # Validate JSON mapping if provided
            if user_input.get("icon_color_mapping"):
                if not self.is_valid_json(user_input["icon_color_mapping"]):
                    errors["icon_color_mapping"] = "invalid_json"

            # Check for duplicate entries
            if not errors:
                existing_entry = await self._async_entry_exists(user_input)
                if existing_entry:
                    errors["base"] = "duplicate_entry"
                    _LOGGER.warning("A duplicate UK Bin Collection entry was found.")

            if not errors:
                # Map selected wiki_name back to council key
                council_key = self.map_wiki_name_to_council_key(user_input["council"])
                if not council_key:
                    errors["council"] = "council"
                    return self.async_show_form(
                        step_id="user", data_schema=..., errors=errors
                    )
                user_input["council"] = council_key

                # Add original_parser if it's an alias
                if "original_parser" in self.councils_data[council_key]:
                    user_input["original_parser"] = self.councils_data[council_key][
                        "original_parser"
                    ]
                user_input["council"] = council_key
                self.data.update(user_input)

                _LOGGER.debug("Mapped council selection to %s", council_key)

                # Proceed to the council step
                return await self.async_step_council()

        # Show the initial form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("name"): cv.string,
                    vol.Required("council"): vol.In(self.council_options),
                    vol.Optional("manual_refresh_only", default=True): bool,
                    vol.Optional("icon_color_mapping", default=""): cv.string,
                }
            ),
            errors=errors,
            description_placeholders={"cancel": "Press Cancel to abort setup."},
        )

    async def async_step_council(self, user_input: Optional[Dict[str, Any]] = None):
        """Second step to configure the council details."""
        errors = {}
        council_key = self.data.get("council")
        council_info = self.councils_data.get(council_key, {})
        requires_selenium = "web_driver" in council_info

        if user_input is not None:
            _LOGGER.debug("Council input fields received: %s", sorted(user_input))
            # Validate JSON mapping if provided
            if user_input.get("icon_color_mapping"):
                if not self.is_valid_json(user_input["icon_color_mapping"]):
                    errors["icon_color_mapping"] = "invalid_json"

            candidate = {**self.data, **user_input}
            apply_registry_metadata(candidate, council_key, council_info)
            errors.update(validate_council_input(council_info, candidate))

            # If no errors, create the config entry
            if not errors:
                self.data = candidate
                _LOGGER.info(
                    "%s Creating config entry for council %s",
                    LOG_PREFIX,
                    council_key,
                )
                return self.async_create_entry(title=self.data["name"], data=self.data)
            else:
                _LOGGER.debug("Errors in council step: %s", errors)

        # Prepare description placeholders
        description_placeholders = {}
        if requires_selenium:
            description = await self.perform_selenium_checks(council_key)
            description_placeholders["selenium_message"] = description
        else:
            description_placeholders["selenium_message"] = ""

        # Show the form
        return self.async_show_form(
            step_id="council",
            data_schema=await self.get_council_schema(council_key, user_input or {}),
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_reconfigure(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle reconfiguration of the integration."""
        return await self.async_step_reconfigure_confirm()

    async def async_step_reconfigure_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ):
        """Handle a reconfiguration flow initialized by the user."""
        errors = {}
        existing_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if existing_entry is None:
            _LOGGER.error("Reconfiguration failed: Config entry not found.")
            return self.async_abort(reason="reconfigure_failed")

        if self.councils_data is None:
            self.councils_data = await self.get_councils_json()
            if not self.councils_data:
                return self.async_abort(reason="council_data_unavailable")
            self.council_names = list(self.councils_data.keys())
            self.council_options = [
                self.councils_data[name]["wiki_name"] for name in self.council_names
            ]
            _LOGGER.debug("Loaded council data for reconfiguration.")

        council_key = existing_entry.data.get("council")
        council_info = self.councils_data.get(council_key, {})
        council_wiki_name = council_info.get("wiki_name", "")

        if user_input is not None:
            _LOGGER.debug("Reconfigure fields received: %s", sorted(user_input))
            # Map selected wiki_name back to council key
            existing_council_key = existing_entry.data.get("council", "")
            council_key = self.map_wiki_name_to_council_key(user_input["council"])
            if not council_key:
                errors["council"] = "council"
                council_key = existing_council_key
            elif council_key != existing_council_key:
                # A council change needs a fresh schema before any address fields
                # can be accepted. Existing-entry flows are deliberately immutable
                # so stale postcode/UPRN/WebDriver values cannot cross councils.
                errors["council"] = "council_change_not_supported"
                council_key = existing_council_key
            council_info = self.councils_data.get(council_key, {})

            # Validate update_interval
            update_interval = user_input.get("update_interval")
            if update_interval is not None:
                try:
                    update_interval = int(update_interval)
                    if update_interval < 1:
                        errors["update_interval"] = "invalid_update_interval"
                except ValueError:
                    errors["update_interval"] = "invalid_update_interval"

            # Validate JSON mapping if provided
            if user_input.get("icon_color_mapping"):
                if not self.is_valid_json(user_input["icon_color_mapping"]):
                    errors["icon_color_mapping"] = "invalid_json"

            data = merge_council_data(
                existing_entry.data,
                user_input,
                previous_council=existing_entry.data.get("council", ""),
                selected_council=council_key,
            )
            apply_registry_metadata(data, council_key, council_info)
            errors.update(validate_council_input(council_info, data))

            if not errors:
                data["icon_color_mapping"] = user_input.get("icon_color_mapping", "")

                self.hass.config_entries.async_update_entry(
                    existing_entry,
                    title=user_input.get("name", existing_entry.title),
                    data=data,
                )
                # Trigger a data refresh by reloading the config entry
                await self.hass.config_entries.async_reload(existing_entry.entry_id)
                _LOGGER.info(
                    "Configuration updated for entry: %s", existing_entry.entry_id
                )
                return self.async_abort(reason="reconfigure_successful")
            else:
                _LOGGER.debug("Errors in reconfiguration: %s", errors)

        # Build the schema with existing data
        schema_data = (
            {**existing_entry.data, **user_input}
            if user_input is not None
            else dict(existing_entry.data)
        )
        schema_data["council"] = council_key
        council_wiki_name = self.councils_data.get(council_key, {}).get(
            "wiki_name", council_wiki_name
        )
        schema = self.build_reconfigure_schema(schema_data, council_wiki_name)

        return self.async_show_form(
            step_id="reconfigure_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={"selenium_message": ""},
        )

    async def get_councils_json(self) -> Dict[str, Any]:
        """Fetch the shared normalized council registry."""
        return await async_fetch_council_registry()

    async def get_council_schema(
        self, council: str, existing_data: Mapping[str, Any] | None = None
    ) -> vol.Schema:
        """Generate the form schema based on council requirements."""
        council_info = self.councils_data.get(council, {})
        existing_data = existing_data or {}
        fields = {}
        add_registry_fields(fields, council_info, existing_data)

        fields[vol.Optional("timeout", default=existing_data.get("timeout", 60))] = (
            vol.All(vol.Coerce(int), vol.Range(min=10))
        )

        fields[
            vol.Optional(
                "update_interval", default=existing_data.get("update_interval", 12)
            )
        ] = vol.All(cv.positive_int, vol.Range(min=1))

        return vol.Schema(fields)

    def build_reconfigure_schema(
        self, existing_data: Dict[str, Any], council_wiki_name: str
    ) -> vol.Schema:
        """Build reconfigure fields from the registry, not saved-key presence."""
        council_info = (self.councils_data or {}).get(
            existing_data.get("council", ""), {}
        )
        fields = {
            vol.Required("name", default=existing_data.get("name", "")): str,
            vol.Required("council", default=council_wiki_name): vol.In(
                [council_wiki_name]
            ),
            vol.Optional(
                "manual_refresh_only",
                default=existing_data.get("manual_refresh_only", True),
            ): bool,
            vol.Required(
                "update_interval", default=existing_data.get("update_interval", 12)
            ): vol.All(cv.positive_int, vol.Range(min=1)),
        }
        add_registry_fields(fields, council_info, existing_data)
        fields[vol.Optional("timeout", default=existing_data.get("timeout", 60))] = (
            vol.All(vol.Coerce(int), vol.Range(min=10))
        )

        fields[
            vol.Optional(
                "icon_color_mapping",
                default=existing_data.get("icon_color_mapping", ""),
            )
        ] = str

        return vol.Schema(fields)

    async def perform_selenium_checks(self, council_key: str) -> str:
        """Perform Selenium and Chromium checks and return a formatted message."""
        messages = []
        council_info = self.councils_data.get(council_key, {})
        council_name = council_info.get("wiki_name", council_key)

        custom_selenium_url = self.data.get("web_driver")
        selenium_results = await self.check_selenium_server(custom_selenium_url)
        self.selenium_available = any(accessible for _, accessible in selenium_results)
        self.selenium_checked = True

        self.chromium_installed = await self.check_chromium_installed()
        self.chromium_checked = True

        # Start building the message with formatted HTML
        messages.append(f"<b>{council_name}</b> requires Selenium to run.<br><br>")

        # Selenium server check results
        messages.append("<b>Remote Selenium server URLs checked:</b><br>")
        for url, accessible in selenium_results:
            status = "✅ Accessible" if accessible else "❌ Not accessible"
            messages.append(f"{url}: {status}<br>")

        # Chromium installation check
        chromium_status = (
            "✅ Installed" if self.chromium_installed else "❌ Not installed"
        )
        messages.append("<br><b>Local Chromium browser check:</b><br>")
        messages.append(f"Chromium browser is {chromium_status}.")

        # Combine messages
        return "".join(messages)

    async def check_selenium_server(self, custom_url: Optional[str] = None) -> list:
        """Check if Selenium servers are accessible."""
        urls = SELENIUM_SERVER_URLS.copy()
        if custom_url:
            urls.insert(0, custom_url)

        results = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.get(url, timeout=5) as response:
                        response.raise_for_status()
                        accessible = response.status == 200
                        results.append((url, accessible))
                        _LOGGER.debug("A configured Selenium endpoint is accessible.")
                except aiohttp.ClientError:
                    _LOGGER.warning("A configured Selenium endpoint is unavailable.")
                    results.append((url, False))
                except Exception:
                    _LOGGER.warning(
                        "Unexpected failure while checking a Selenium endpoint."
                    )
                    results.append((url, False))
        return results

    async def check_chromium_installed(self) -> bool:
        """Check if Chromium is installed."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._sync_check_chromium)
        if result:
            _LOGGER.debug("Chromium is installed.")
        else:
            _LOGGER.warning("Chromium is not installed.")
        return result

    def _sync_check_chromium(self) -> bool:
        """Synchronous check for Chromium installation."""
        for exec_name in BROWSER_BINARIES:
            try:
                if shutil.which(exec_name):
                    _LOGGER.debug(f"Found Chromium executable: {exec_name}")
                    return True
            except Exception as e:
                _LOGGER.error(
                    "Executable availability check failed for '%s' (%s)",
                    exec_name,
                    type(e).__name__,
                )
                continue  # Continue checking other binaries
        _LOGGER.debug("No Chromium executable found.")
        return False

    def map_wiki_name_to_council_key(self, wiki_name: str) -> str:
        """Map the council wiki name back to the council key."""
        try:
            index = self.council_options.index(wiki_name)
            council_key = self.council_names[index]
            _LOGGER.debug(
                "Mapped wiki name '%s' to council key '%s'.", wiki_name, council_key
            )
            return council_key
        except ValueError:
            _LOGGER.error("Wiki name '%s' not found in council options.", wiki_name)
            return ""

    @staticmethod
    def is_valid_json(json_str: str) -> bool:
        """Validate if a string is valid JSON."""
        try:
            json.loads(json_str)
            return True
        except json.JSONDecodeError as e:
            _LOGGER.debug("JSON decode error (%s)", type(e).__name__)
            return False

    async def _async_entry_exists(
        self, user_input: Dict[str, Any]
    ) -> Optional[config_entries.ConfigEntry]:
        """Check if a config entry with the same name or data already exists."""
        for entry in self._async_current_entries():
            if entry.data.get("name") == user_input.get("name"):
                return entry
            if entry.data.get("council") == user_input.get(
                "council"
            ) and entry.data.get("url") == user_input.get("url"):
                return entry
        return None

    async def async_step_import(
        self, import_config: Dict[str, Any]
    ) -> config_entries.FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_config)


class UkBinCollectionOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for UkBinCollection."""

    councils_data: Optional[Dict[str, Any]] = None
    council_names: list = []
    council_options: list = []

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        existing_data = self.config_entry.data

        # Fetch council data
        self.councils_data = await self.get_councils_json()
        if not self.councils_data:
            _LOGGER.error("Council data is unavailable for options flow.")
            return self.async_abort(reason="council_data_unavailable")

        self.council_names = list(self.councils_data.keys())
        self.council_options = [
            self.councils_data[name]["wiki_name"] for name in self.council_names
        ]
        _LOGGER.debug("Loaded council data for options flow.")

        if user_input is not None:
            _LOGGER.debug("Options fields received: %s", sorted(user_input))
            # Map selected wiki_name back to council key
            existing_council_key = existing_data.get("council", "")
            council_key = self.map_wiki_name_to_council_key(user_input["council"])
            if not council_key:
                errors["council"] = "council"
                council_key = existing_council_key
            elif council_key != existing_council_key:
                errors["council"] = "council_change_not_supported"
                council_key = existing_council_key
            council_info = self.councils_data.get(council_key, {})

            # Validate update_interval
            update_interval = user_input.get("update_interval")
            if update_interval is not None:
                try:
                    update_interval = int(update_interval)
                    if update_interval < 1:
                        errors["update_interval"] = "invalid_update_interval"
                except ValueError:
                    errors["update_interval"] = "invalid_update_interval"

            # Validate JSON mapping if provided
            if user_input.get("icon_color_mapping"):
                if not UkBinCollectionConfigFlow.is_valid_json(
                    user_input["icon_color_mapping"]
                ):
                    errors["icon_color_mapping"] = "invalid_json"

            data = merge_council_data(
                existing_data,
                user_input,
                previous_council=existing_data.get("council", ""),
                selected_council=council_key,
            )
            apply_registry_metadata(data, council_key, council_info)
            errors.update(validate_council_input(council_info, data))

            if not errors:
                data["icon_color_mapping"] = user_input.get("icon_color_mapping", "")

                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=data,
                )
                # Trigger a data refresh by reloading the config entry
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                _LOGGER.info("Options updated and config entry reloaded.")
                return self.async_create_entry(title="", data={})
            else:
                _LOGGER.debug("Errors in options flow: %s", errors)

        # Build the form with existing data
        schema_data = (
            {**existing_data, **user_input}
            if user_input is not None
            else dict(existing_data)
        )
        schema_data["council"] = (
            council_key if user_input is not None else existing_data.get("council", "")
        )
        schema = self.build_options_schema(schema_data)

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={"cancel": "Press Cancel to abort setup."},
        )

    async def get_councils_json(self) -> Dict[str, Any]:
        """Fetch the same normalized registry used by setup and reconfigure."""
        return await async_fetch_council_registry()

    def build_options_schema(self, existing_data: Dict[str, Any]) -> vol.Schema:
        """Build options fields from the current registry contract."""
        council_current_key = existing_data.get("council", "")
        council_info = (self.councils_data or {}).get(council_current_key, {})
        try:
            council_current_wiki = self.council_options[
                self.council_names.index(council_current_key)
            ]
        except (ValueError, IndexError):
            council_current_wiki = ""

        fields = {
            vol.Required("name", default=existing_data.get("name", "")): str,
            vol.Required("council", default=council_current_wiki): vol.In(
                [council_current_wiki]
            ),
            vol.Optional(
                "manual_refresh_only",
                default=existing_data.get("manual_refresh_only", True),
            ): bool,
            vol.Required(
                "update_interval", default=existing_data.get("update_interval", 12)
            ): vol.All(cv.positive_int, vol.Range(min=1)),
        }

        add_registry_fields(fields, council_info, existing_data)
        fields[vol.Optional("timeout", default=existing_data.get("timeout", 60))] = (
            vol.All(vol.Coerce(int), vol.Range(min=10))
        )
        fields[
            vol.Optional(
                "icon_color_mapping",
                default=existing_data.get("icon_color_mapping", ""),
            )
        ] = cv.string

        return vol.Schema(fields)

    def map_wiki_name_to_council_key(self, wiki_name: str) -> str:
        """Map the council wiki name back to the council key."""
        try:
            index = self.council_options.index(wiki_name)
            council_key = self.council_names[index]
            _LOGGER.debug(
                "Mapped wiki name '%s' to council key '%s'.", wiki_name, council_key
            )
            return council_key
        except ValueError:
            _LOGGER.error("Wiki name '%s' not found in council options.", wiki_name)
            return ""

    @staticmethod
    def is_valid_json(json_str: str) -> bool:
        """Validate if a string is valid JSON."""
        try:
            json.loads(json_str)
            return True
        except json.JSONDecodeError as e:
            _LOGGER.debug("JSON decode error in options flow (%s)", type(e).__name__)
            return False


@callback
def async_get_options_flow(config_entry):
    """Backward-compatible wrapper around the registered options callback."""
    return UkBinCollectionConfigFlow.async_get_options_flow(config_entry)
