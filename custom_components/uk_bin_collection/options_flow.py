"""Options flow for UK Bin Collection integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .initialisation import initialisation_data
from .utils import (
    build_user_schema,
    build_council_schema,
    build_selenium_schema,
    build_advanced_schema,
    prepare_config_data,
    validate_selenium_config
)

_LOGGER = logging.getLogger(__name__)

class UkBinCollectionOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for UkBinCollection."""

    def __init__(self, config_entry):
        """Initialise options flow."""
        # self.config_entry = config_entry # deprecated
        
        # Initialise self.options with existing options
        self.options = dict(config_entry.options)
        
        # Initialise self.data from config_entry data
        self.data = dict(config_entry.data) if config_entry.data else {}
        self._initialised = False 
        
        # IMPORTANT: Ensure council is initialised from the start
        # If council doesn't exist in config data but original_parser does, use that
        if not self.data.get("council") and self.data.get("original_parser"):
            self.data["council"] = self.data["original_parser"]
            
        # Log the initial state for debugging
        _LOGGER.debug(f"Options flow initialised with council: {self.data.get('council')}, original_parser: {self.data.get('original_parser')}")
        
    async def async_step_init(self, user_input=None):
        """First step in options flow - redirect to user selection."""
        # Initialise the handler with councils data  
        if not self._initialised:  
            await initialisation_data(self)
            self._initialised = True  
            
        # Redirect to the first step (user selection)
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Step 1: Select Council."""
        errors = {}
        
        # Create a mapping of wiki names to council keys
        council_list = self.data.get("council_list", {})
        wiki_names_map = {}
        
        for council_key, council_data in council_list.items():
            wiki_name = council_data.get("wiki_name", council_key)
            wiki_names_map[wiki_name] = council_key
        
        # Sort wiki names for the dropdown
        wiki_names = sorted(wiki_names_map.keys())
        
        # Get the current council key and original parser from the config entry
        current_council_key = self.data.get("council", "")
        current_original_parser = self.data.get("original_parser", "")
        current_wiki_name = None
        
        # Debug logging to see what we're working with
        _LOGGER.debug(f"Looking up council for: council={current_council_key}, original_parser={current_original_parser}")
        
        for wiki_name, council_key in wiki_names_map.items():

            # Match by exact council key
            if council_key == current_council_key:
                current_wiki_name = wiki_name
                _LOGGER.debug(f"Found council by exact match: {wiki_name}")
                break
            
        # Log the result
        if current_wiki_name:
            _LOGGER.debug(f"Using {current_wiki_name} as the selected council")
        else:
            _LOGGER.warning(f"Could not find matching council for {current_council_key}")
        
        # Get default name
        current_name = self.data.get("name", "")
        
        schema = build_user_schema(
            wiki_names=wiki_names,
            default_name=current_name,
            default_council=current_wiki_name,
            include_test_data=True 
        )
        
        if user_input is not None:
            selected_wiki_name = user_input.get("selected_council")
            council_key = wiki_names_map.get(selected_wiki_name)
            
            # Update the data with both the display name and internal key
            self.data["name"] = user_input.get("name")
            self.data["selected_wiki_name"] = selected_wiki_name
            self.data["selected_council"] = council_key
            
            # Store whether to use test data
            self.data["use_test_data"] = user_input.get("use_test_data", False)

            # Preserve the original_parser if present in council data
            council_data = council_list.get(council_key, {})
            if "original_parser" in council_data:
                self.data["original_parser"] = council_data["original_parser"]
                _LOGGER.debug(f"Using original_parser '{council_data['original_parser']}' for council {council_key}")
            
            if not errors:
                return await self.async_step_council_info()

        # Dynamically set the description placeholders
        description_placeholders = {
            "step_user_description": "Modify your bin collection configuration."
        }

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
        wiki_command_url_override = council_data.get("wiki_command_url_override", "")

        if user_input is not None:
            # Check if URL is required and hasn't been modified
            if user_input.get("url") == wiki_command_url_override and wiki_command_url_override:
                errors["base"] = "url_not_modified"
                _LOGGER.warning("URL was not modified but is required for this council")
            
            if not errors:
                self.data.update(user_input)
                council_key = self.data.get("selected_council", "")
                council_data = self.data.get("council_list", {}).get(council_key, {})

                # If this council does not require Selenium, skip to advanced
                if not council_data.get("web_driver"):
                    return await self.async_step_advanced()
                return await self.async_step_selenium()

        # Get current values from config entry
        default_values = {
            "postcode": self.data.get("postcode", ""),
            "uprn": self.data.get("uprn", ""),
            "house_number": self.data.get("number", ""), 
            "usrn": self.data.get("usrn", ""),
            "url": self.data.get("url", wiki_command_url_override)
        }

        # If user selected to use test data, replace with values from council_data
        if self.data.get("use_test_data", False):
            _LOGGER.debug(f"Using test data for council {council_key}")
            
            # Map the test data fields to the form fields
            if "postcode" in council_data:
                default_values["postcode"] = council_data["postcode"]
            if "house_number" in council_data:
                default_values["house_number"] = council_data["house_number"]
            if "uprn" in council_data:
                default_values["uprn"] = council_data["uprn"]
            if "usrn" in council_data:
                default_values["usrn"] = council_data["usrn"]
            if "url" in council_data:
                default_values["url"] = council_data["url"]
                
            _LOGGER.debug(f"Test data values: {default_values}")

        wiki_note = council_data.get("wiki_note", "No additional notes available for this council.")
        
        description_placeholders = {
            "step_council_info_description": wiki_note
        }

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

        # Initialise selenium_status if missing
        if "selenium_status" not in self.data:
            self.data["selenium_status"] = {}

        # Get current selenium settings
        current_web_driver = self.data.get("web_driver", "")
        
        # Use the schema builder instead of manually creating a schema
        schema = build_selenium_schema(default_url=current_web_driver)

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
        """Handle advanced options."""
        if user_input is not None:
            # User submitted the form - pass is_options_flow=True to skip critical field validation
            self.options.update(prepare_config_data(user_input, is_options_flow=True))
            return self.async_create_entry(title="", data=self.options)
        
        # Get defaults from current config - use self instead of passing config_entry
        defaults = get_advanced_defaults(self)
        
        # Create schema with the defaults
        schema = build_advanced_schema(defaults)
        
        return self.async_show_form(
            step_id="advanced",
            data_schema=schema,
        )

# When loading settings for the options flow
def get_advanced_defaults(options_flow):
    """Get defaults for advanced settings from the config entry."""
    # Access the config_entry through the options_flow instance
    config_entry = options_flow.config_entry
    
    defaults = {
        # Map from manual_refresh_only to automatically_refresh
        # Note: They represent the same setting but with different names
        # Also see the field_mappings section in prepare_config_data in utils.py
        "automatically_refresh": config_entry.options.get(
            "manual_refresh_only",  
            config_entry.data.get("manual_refresh_only", True)
        ),
        "update_interval": config_entry.options.get(
            "update_interval", 
            config_entry.data.get("update_interval", 12)
        ),
        "timeout": config_entry.options.get(
            "timeout", 
            config_entry.data.get("timeout", 60)
        ),
        "icon_color_mapping": config_entry.options.get(
            "icon_color_mapping", 
            config_entry.data.get("icon_color_mapping", "")
        )
    }
    return defaults