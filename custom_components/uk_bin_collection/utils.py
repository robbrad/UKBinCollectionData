import json
import aiohttp
import logging
import asyncio
import voluptuous as vol
import shutil
import re

from typing import Dict, Any, Optional
from .const import BROWSER_BINARIES
from homeassistant import config_entries

_LOGGER = logging.getLogger(__name__)

# -----------------------------------------------------
# 🔄 Fetch Data
# -----------------------------------------------------

async def get_councils_json(url: str = None) -> Dict[str, Any]:
    """
    Fetch council data from a JSON URL.
    
    This function can handle both data formats:
    - Old format: Where GooglePublicCalendarCouncil contains supported_councils
    - New format: Where councils directly reference GooglePublicCalendarCouncil via original_parser
    
    This function ensures the output is consistent regardless of input format, maintaining
    the same user experience by preserving council names in the wiki_name field.
    
    Args:
        url: URL to fetch councils data from. If None, uses the default URL from constants.
    
    Returns:
        Dictionary of council data, sorted alphabetically by council ID.
    """
    from .const import COUNCIL_DATA_URL
    
    if url is None:
        url = COUNCIL_DATA_URL
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                response.raise_for_status()
                data_text = await response.text()
                council_data = json.loads(data_text)
                
                # Check if we're dealing with the old format by looking for supported_councils in GooglePublicCalendarCouncil
                is_old_format = "GooglePublicCalendarCouncil" in council_data and "supported_councils" in council_data["GooglePublicCalendarCouncil"]
                
                normalised_data = {}
                
                if is_old_format:
                    _LOGGER.debug("Detected old format JSON (input.json style)")
                    # Process old format
                    for key, value in council_data.items():
                        normalised_data[key] = value
                        # If this is GooglePublicCalendarCouncil, process its supported councils
                        if key == "GooglePublicCalendarCouncil" and "supported_councils" in value:
                            for alias in value.get("supported_councils", []):
                                alias_data = value.copy()
                                alias_data["original_parser"] = key
                                alias_data["wiki_command_url_override"] = "https://calendar.google.com/calendar/ical/XXXXX%40group.calendar.google.com/public/basic.ics"
                                alias_data["wiki_name"] = alias
                                if "wiki_note" in value:
                                    alias_data["wiki_note"] = value["wiki_note"]
                                normalised_data[alias] = alias_data
                else:
                    _LOGGER.debug("Detected new format JSON (placeholder_input.json style)")
                    # Process new format - all councils are already first-class entries with their own complete data
                    normalised_data = council_data.copy()
                    # No special handling needed for GooglePublicCalendarCouncil councils
                    # as they're already properly defined in the new format
                
                # Sort alphabetically by key (council ID)
                sorted_data = dict(sorted(normalised_data.items()))
                
                _LOGGER.debug("Loaded %d councils", len(sorted_data))
                _LOGGER.debug("Normalised council data: %d entries", len(normalised_data))  
                return sorted_data
            
    except aiohttp.ClientError as e:
        _LOGGER.error("HTTP error fetching council data: %s", e)
        return {}
    except asyncio.TimeoutError:
        _LOGGER.error("Timeout fetching council data from %s", url)
        return {}
    except json.JSONDecodeError as e:
        _LOGGER.error("Invalid JSON in council data: %s", e)
        return {}
    except Exception as e:
        _LOGGER.error("Unexpected error fetching council data: %s", e)
        return {}

async def check_selenium_server(url: str) -> bool:
    """Check if a Selenium server is accessible."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=5) as response:
                accessible = response.status == 200
                # _LOGGER.debug(f"Selenium server at {url} is {'accessible' if accessible else 'not accessible'}")
                return accessible
        except Exception as e:
            # _LOGGER.debug(f"Error checking Selenium server at {url}: {e}")
            return False

async def check_chromium_installed() -> bool:
    """Check if Chromium is installed."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _sync_check_chromium)
    if result:
        _LOGGER.debug("Chromium is installed.")
    else:
        _LOGGER.debug("Chromium is not installed.")
    return result

def _sync_check_chromium() -> bool:
    """Synchronous check for Chromium installation."""
    for exec_name in BROWSER_BINARIES:
        try:
            if shutil.which(exec_name):
                _LOGGER.debug(f"Found Chromium executable: {exec_name}")
                return True
        except Exception as e:
            _LOGGER.debug(
                f"Exception while checking for executable '{exec_name}': {e}"
            )
            continue  # Continue checking other binaries
    _LOGGER.debug("No Chromium executable found.")
    return False

# -----------------------------------------------------
# 🔄 Schema Builders
# -----------------------------------------------------

def build_user_schema(wiki_names, default_name="", default_council=None, include_test_data=False):
    """Build schema for user step."""
    schema_dict = {
        vol.Required("name", default=default_name): str,
        vol.Required("selected_council", default=default_council): vol.In(wiki_names),
    }
    
    # Only include the test data checkbox if specified
    if include_test_data:
        schema_dict[vol.Optional("use_test_data", default=False)] = bool
        
    schema = vol.Schema(schema_dict)
    return schema

def build_council_schema(council_key: str, council_data: Dict[str, Any], defaults: Dict[str, str] = {}) -> vol.Schema:
    """Schema for configuring council-specific information."""
    fields = {}
    if "postcode" in council_data:
        fields[vol.Required("postcode", default=defaults.get("postcode", ""))] = str
    if "uprn" in council_data:
        fields[vol.Required("uprn", default=defaults.get("uprn", ""))] = str
    if "house_number" in council_data:
        fields[vol.Required("house_number", default=defaults.get("house_number", ""))] = str
    if "usrn" in council_data:
        fields[vol.Required("usrn", default=defaults.get("usrn", ""))] = str
    if "wiki_command_url_override" in council_data:
        fields[vol.Optional("url", default=defaults.get("url", ""))] = str

    _LOGGER.debug(f"Building council schema for {council_key} with fields: {list(fields.keys())}")
    return vol.Schema(fields)


def build_selenium_schema(default_url=""):
    """Build schema for Selenium configuration."""
    import homeassistant.helpers.config_validation as cv
    
    # Create the schema with separate options instead of multi-select
    return vol.Schema({
        vol.Optional("web_driver", default=default_url): vol.Coerce(str),
        vol.Optional("headless_mode", default=True): bool,
        vol.Optional("local_browser", default=False): bool,
    })

def build_advanced_schema(defaults=None) -> vol.Schema:
    """Schema for advanced settings configuration."""
    if defaults is None:
        defaults = {
            "automatically_refresh": True,
            "update_interval": 12,
            "timeout": 60,
            "icon_color_mapping": ""
        }
        
    # Get default values with fallbacks
    default_timeout = defaults.get("timeout", 60)  # Default 60 seconds
    default_update_interval = defaults.get("update_interval", 12)  # Default 12 hours
    default_automatically_refresh = defaults.get("automatically_refresh", True)
    default_icon_mapping = defaults.get("icon_color_mapping", "")
        
    # _LOGGER.debug("Building advanced schema with defaults: %s", defaults)
    
    schema = vol.Schema({
        vol.Optional("timeout", default=default_timeout): vol.All(
            vol.Coerce(int),  # Convert to integer
            vol.Range(min=10, msg="Timeout must be at least 10 seconds"), 
        ),
        vol.Optional("update_interval", default=default_update_interval): vol.All(
            vol.Coerce(int),  # Convert to integer
            vol.Range(min=1, msg="Update interval must be at least 1 hour"),
        ),
        vol.Optional("automatically_refresh", default=default_automatically_refresh): bool,
        vol.Optional("icon_color_mapping", default=default_icon_mapping): str,
    })
    
    return schema

# -----------------------------------------------------
# 🔄 Utility Functions
# -----------------------------------------------------

def is_valid_json(json_string: str) -> bool:
    """Check if a string is valid JSON."""
    try:
        json.loads(json_string)
        _LOGGER.debug("JSON string is valid.")
        return True
    except ValueError as e:
        _LOGGER.debug(f"Invalid JSON string: {e}")
        return False

def is_valid_json_validator(value):
    """Validator function for JSON strings."""
    if not value:
        return value
    try:
        json.loads(value)
        return value
    except ValueError as e:
        raise vol.Invalid(f"Invalid JSON: {e}")

async def async_entry_exists(
    flow, user_input: Dict[str, Any]
) -> Optional[config_entries.ConfigEntry]:
    """Check if a config entry with the same name or data already exists."""
    for entry in flow._async_current_entries():
        if entry.data.get("name") == user_input.get("name"):
            return entry
        if entry.data.get("council") == user_input.get("council") and entry.data.get("url") == user_input.get("url"):
            return entry
    return None

def prepare_config_data(data: dict, is_options_flow=False) -> dict:
    """Prepare configuration data for saving to config entry.
    
    Ensures critical fields are present and handles field mappings.
    
    Args:
        data: The input data dictionary
        is_options_flow: Whether this is being called from options flow (skips critical field validation)
    """
    import logging
    _LOGGER = logging.getLogger(__name__)
    
    # Define field mappings for parameter name corrections
    field_mappings = {
        "headless_mode": "headless",  # headless_mode should be headless
        "house_number": "number",     # house_number should be number
        # This is confusing, but seems 'manual_refresh_only' actually means 'automatically_refresh'
        # So we map it to 'manual_refresh_only' for the config entry
        # https://github.com/robbrad/UKBinCollectionData/discussions/1449
        "automatically_refresh": "manual_refresh_only", 
    }
    
    # List of essential fields with correct parameter names
    essential_fields = [
        "council",
        "name", 
        "postcode", 
        "uprn", 
        "number",  
        "usrn", 
        "url", 
        "original_parser",
        "skip_get_url",
        "web_driver", 
        "headless",
        "local_browser",
        "manual_refresh_only", 
        "update_interval", 
        "timeout", 
        "icon_color_mapping"
    ]
    
    # Start with council to ensure it's always present
    council_key = data.get("selected_council") or data.get("council", "")
    filtered_data = {}
    
    # Always include council if available (critical field)
    if council_key:
        filtered_data["council"] = council_key
    
    # Handle URL defaulting to council's URL if not provided by user
    url = data.get("url")
    if not url and council_key:
        # Get council data to find default URL
        council_data = data.get("council_list", {}).get(council_key, {})
        url = council_data.get("url", "")
    
    # Add URL to filtered_data if we have one
    if url:
        filtered_data["url"] = url

    # Handle skip_get_url parameter from council data
    if council_key:
        council_data = data.get("council_list", {}).get(council_key, {})
        skip_get_url = council_data.get("skip_get_url")
        if skip_get_url is not None:  # Only add it if it has an actual value
            filtered_data["skip_get_url"] = skip_get_url

    # If there's an original_parser, ensure it's preserved
    if data.get("original_parser"):
        filtered_data["original_parser"] = data["original_parser"]
    
    # Process remaining fields
    for field in essential_fields:
        # Skip council and original_parser as we've already handled them
        if field in ["council", "original_parser"]:
            continue
            
        # Check if this field has a mapping (old name → new name)
        old_field = next((old for old, new in field_mappings.items() if new == field), field)
        
        # Get value using the old field name from data
        value = data.get(old_field)
        
        # If value exists, add it to filtered_data with the correct field name
        if value is not None:
            filtered_data[field] = value

    # Log the final data for debugging
    _LOGGER.debug(f"Prepared configuration data: {filtered_data}")
    
    # Skip validation for critical fields in options flow since they're preserved in the entry
    if not is_options_flow:
        # Validate critical fields only for initial config
        if not filtered_data.get("council") and not filtered_data.get("original_parser"):
            _LOGGER.error("Critical error: Neither council nor original_parser specified in final data")
            raise ValueError("Missing council specification in configuration")
        
    return filtered_data

async def validate_selenium_config(user_input, data_dict):
    """Validate Selenium configuration and determine if we can proceed.
    
    Args:
        user_input: User input dictionary from the form
        data_dict: Data dictionary to update with configuration results
        
    Returns:
        tuple: (can_proceed, error_code)
            - can_proceed: True if we can proceed to next step, False otherwise
            - error_code: Error code if can_proceed is False, None otherwise
    """
    import logging
    _LOGGER = logging.getLogger(__name__)
    
    # Get user selections
    use_local_browser = user_input.get("local_browser", False)
    web_driver_url = user_input.get("web_driver", "").strip()
    
    # Update data dictionary with user input
    data_dict.update(user_input)
    
    # Check if Selenium server is accessible
    if web_driver_url and use_local_browser == False:
        is_accessible = await check_selenium_server(web_driver_url)

        if is_accessible:
            _LOGGER.debug(f"Selected Selenium URL {web_driver_url} is accessible")
            return True, None
        else:
            _LOGGER.debug(f"Selected Selenium URL {web_driver_url} is NOT accessible")
            return False, "selenium_unavailable"
            
    elif use_local_browser:
        # Check if Chromium is installed
        chromium_installed = await check_chromium_installed()
        data_dict["chromium_installed"] = chromium_installed

        if chromium_installed:
            _LOGGER.debug("Local browser selected and Chromium is available")
            return True, None
        else:
            _LOGGER.debug("Local browser selected but Chromium is not installed")
            return False, "chromium_unavailable"
    else:
        # Neither Selenium nor Chromium is available
        _LOGGER.debug("No Selenium method selected (neither URL provided nor local browser enabled)")
        return False, "selenium_unavailable"

def is_valid_postcode(postcode: str) -> bool:
    # Not currently used, because some councils use the postcode field for other purposes
    # UK postcode regex pattern
    postcode_regex = r"^(GIR 0AA|[A-PR-UWYZ][A-HK-Y]?[0-9][0-9A-HJKSTUW]? ?[0-9][ABD-HJLNP-UW-Z]{2})$"
    return re.match(postcode_regex, postcode.replace(" ", "").upper()) is not None

    # Examples
    #print(is_valid_postcode("SW1A 1AA"))  # True
    #print(is_valid_postcode("INVALID"))   # False

def is_valid_uprn(uprn: str) -> bool:
    # Not currently used, because some councils use the UPRN field for other purposes
    return uprn.isdigit() and len(uprn) <= 12
    
    # Examples
    # print(is_valid_uprn("100021066689"))  # True
    # print(is_valid_uprn("ABCD12345678"))  # False
