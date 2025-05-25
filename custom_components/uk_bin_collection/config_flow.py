from homeassistant import config_entries
from homeassistant.core import callback
from .initialisation import initialisation_data
from .options_flow import UkBinCollectionOptionsFlowHandler

import logging
from .utils import (
    build_user_schema,
    build_council_schema,
    build_selenium_schema,
    build_advanced_schema,
    async_entry_exists,
    is_valid_json,
    prepare_config_data,
    validate_selenium_config
)

_LOGGER = logging.getLogger(__name__)

class BinCollectionConfigFlow(config_entries.ConfigFlow, domain="uk_bin_collection"):
    """Config flow for Bin Collection Data."""
    
    VERSION = 3
    
    def __init__(self):
        """Initialise the config flow.""" 
        self.data = {}
        self._initialised = False 

    async def async_step_user(self, user_input=None):
        """Step 1: Select Council."""
        
        errors = {}
        
        # Only run initialisation once if not already initialised  # Changed both instances
        if not self._initialised:  
            await initialisation_data(self)
            self._initialised = True  
        
        # Create a mapping of wiki names to council keys
        council_list = self.data.get("council_list", {})
        wiki_names_map = {}
        
        for council_key, council_data in council_list.items():
            wiki_name = council_data.get("wiki_name", council_key)
            wiki_names_map[wiki_name] = council_key
        
        # Sort wiki names for the dropdown
        wiki_names = sorted(wiki_names_map.keys())
        
        # Get detected council name (if available)
        detected_council_key = self.data.get("detected_council", None)
        detected_council_name = None
        if detected_council_key and detected_council_key in council_list:
            detected_council_name = council_list[detected_council_key].get("wiki_name")
        
        # Get default name (street name from property info)
        default_name = self.data.get("property_info", {}).get("street_name", "")

        council_key = self.data.get("selected_council", "")
        if council_key in council_list:
            default_council = council_list[council_key].get("wiki_name", council_key)
        else:
            default_council = detected_council_name or ""
                
        schema = build_user_schema(
            wiki_names=wiki_names,
            default_name=self.data.get("name", default_name),
            default_council=default_council
        )

        if user_input is not None:
            selected_wiki_name = user_input.get("selected_council")
            council_key = wiki_names_map.get(selected_wiki_name)
            
            # Update the data with both the display name and internal key
            self.data["name"] = user_input.get("name")
            self.data["selected_wiki_name"] = selected_wiki_name
            self.data["selected_council"] = council_key
            
            # Preserve the original_parser if present in council data
            council_data = council_list.get(council_key, {})
            if "original_parser" in council_data:
                self.data["original_parser"] = council_data["original_parser"]
                _LOGGER.debug(f"Using original_parser '{council_data['original_parser']}' for council {council_key}")
            
            existing_entry = await async_entry_exists(self, user_input)
            if existing_entry:
                errors["base"] = "duplicate_entry"
                _LOGGER.warning(
                    "Duplicate entry found: %s", existing_entry.data.get("name")
                )
            
            if not errors:
                return await self.async_step_council_info()

        # Dynamically set the description placeholders
        description_placeholders = {}
        if detected_council_name:
            description_placeholders["step_user_description"] = "Council auto-selected based on location."
            _LOGGER.debug("Detected council: %s", detected_council_name)
        else:
            description_placeholders["step_user_description"] = f"Please [contact us](https://github.com/robbrad/UKBinCollectionData#requesting-your-council) if your council isn't listed."
            _LOGGER.debug("No council detected.")

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )
    
    async def async_step_council_info(self, user_input=None):
        """Step 2: Configure Council Information."""
        errors = {}

        council_key = self.data.get("selected_council", "")
        council_data = self.data.get("council_list", {}).get(council_key, {})
        wiki_command_url = council_data.get("wiki_command_url_override", "")

        if user_input is not None:
            # Check if URL needs modification but user didn't change it
            if (wiki_command_url and                                   # Council has a wiki_command_url
                wiki_command_url != council_data.get("url", "") and    # wiki_command_url is different from existing council URL
                user_input.get("url") == wiki_command_url):            # User didn't modify the pre-filled URL
                
                errors["base"] = "url_not_modified"
                _LOGGER.warning("URL was not modified but requires customization for this council")
                
            if not errors:
                self.data.update(user_input)
                council_key = self.data.get("selected_council", "")
                council_data = self.data.get("council_list", {}).get(council_key, {})

                # If this council does not require Selenium, skip to advanced
                if not council_data.get("web_driver"):
                    return await self.async_step_advanced()
                return await self.async_step_selenium()

        default_values = {
            "postcode": self.data.get("detected_postcode", self.data.get("postcode", "")),
            "url": self.data.get("url", wiki_command_url)
        }

        wiki_note = council_data.get("wiki_note", "No additional notes available for this council.")
        
        description_placeholders = {}
        description_placeholders["step_council_info_description"] = wiki_note

        schema = build_council_schema(council_key, council_data, default_values)

        return self.async_show_form(
            step_id="council_info",
            data_schema=schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_selenium(self, user_input=None):
        """Step 3: Selenium configuration."""
        
        errors = {}

        # Debug to see what's in self.data
        _LOGGER.debug(f"Selenium step data keys: {list(self.data.keys())}")
        if "selenium_status" in self.data:
            _LOGGER.debug(f"Selenium status: {self.data['selenium_status']}")
        else:
            _LOGGER.warning("No selenium_status in self.data")
            # Initialise it if missing 
            self.data["selenium_status"] = {}

        # Get default selenium URL (first working one)
        selenium_url = next((url for url, status in self.data["selenium_status"].items() if status), 
                           self.data.get("web_driver", ""))
                           
        schema = build_selenium_schema(selenium_url)

        if user_input is not None:
            # Use the shared function to validate selenium config
            can_proceed, error_code = await validate_selenium_config(user_input, self.data)
            
            if can_proceed:
                return await self.async_step_advanced()
            elif error_code:
                errors["base"] = error_code

        description_placeholders = {}

        return self.async_show_form(
            step_id="selenium",
            data_schema=schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_advanced(self, user_input=None):
        """Step 4: Advanced configuration."""
        errors = {}

        # Get current advanced settings
        advanced_defaults = {
            "automatically_refresh": self.data.get("automatically_refresh", True), 
            "update_interval": self.data.get("update_interval", 12),
            "timeout": self.data.get("timeout", 60),
            "icon_color_mapping": self.data.get("icon_color_mapping", "")
        }

        schema = build_advanced_schema(defaults=advanced_defaults)

        if user_input is not None:
            # Check if icon_color_mapping is valid JSON if provided
            if user_input.get("icon_color_mapping"):
                if not is_valid_json(user_input["icon_color_mapping"]):
                    errors["icon_color_mapping"] = "invalid_json"
                    _LOGGER.warning("Invalid JSON in icon_color_mapping field")
            
            if not errors:
                self.data.update(user_input)
                
                try:
                    # Use the shared function to prepare the data
                    filtered_data = prepare_config_data(self.data)
                    
                    _LOGGER.debug(f"Final configuration: {filtered_data}")
                    return self.async_create_entry(title=filtered_data["name"], data=filtered_data)
                        
                except Exception as e:
                    # Handle other errors
                    errors["base"] = "unknown_error"
                    _LOGGER.exception(f"Error preparing configuration data: {e}")

        return self.async_show_form(
            step_id="advanced",
            data_schema=schema,
            errors=errors
        )
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return UkBinCollectionOptionsFlowHandler(config_entry)

