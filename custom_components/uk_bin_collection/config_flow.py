import json
import logging

import aiohttp
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries

from typing import Any


_LOGGER = logging.getLogger(__name__)

from .const import DOMAIN, LOG_PREFIX


class UkBinCollectionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    def __init__(self):
        self.councils_data = None

    async def get_councils_json(self) -> object:
        """Returns an object of supported council's and their required fields."""
        # Fetch the JSON data from the provided URL
        url = "https://raw.githubusercontent.com/robbrad/UKBinCollectionData/0.91.2/uk_bin_collection/tests/input.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data_text = await response.text()
                return json.loads(data_text)

    async def get_council_schema(self, council=str) -> vol.Schema:
        """Returns a config flow form schema based on a specific council's fields."""
        if self.councils_data is None:
            self.councils_data = await self.get_councils_json()
        council_schema = vol.Schema({})
        if (
            "skip_get_url" not in self.councils_data[council]
            or "custom_component_show_url_field" in self.councils_data[council]
        ):
            council_schema = council_schema.extend(
                {vol.Required("url", default=""): cv.string}
            )
        if "uprn" in self.councils_data[council]:
            council_schema = council_schema.extend(
                {vol.Required("uprn", default=""): cv.string}
            )
        if "postcode" in self.councils_data[council]:
            council_schema = council_schema.extend(
                {vol.Required("postcode", default=""): cv.string}
            )
        if "house_number" in self.councils_data[council]:
            council_schema = council_schema.extend(
                {vol.Required("number", default=""): cv.string}
            )
        if "usrn" in self.councils_data[council]:
            council_schema = council_schema.extend(
                {vol.Required("usrn", default=""): cv.string}
            )
        if "web_driver" in self.councils_data[council]:
            council_schema = council_schema.extend(
                {vol.Optional("web_driver", default=""): cv.string}
            )
            council_schema = council_schema.extend(
                {vol.Optional("headless", default=True): bool}
            )
            council_schema = council_schema.extend(
                {vol.Optional("local_browser", default=False): bool}
            )

            # Add timeout field with default value of 60 seconds
        council_schema = council_schema.extend(
            {
                vol.Optional("timeout", default=60): vol.All(
                    vol.Coerce(int), vol.Range(min=10)
                )
            }
        )

        return council_schema

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        self.councils_data = await self.get_councils_json()
        self.council_names = list(self.councils_data.keys())
        self.council_options = [
            self.councils_data[name]["wiki_name"] for name in self.council_names
        ]

        if user_input is not None:
            if user_input["name"] is None or user_input["name"] == "":
                errors["base"] = "name"
            if user_input["council"] is None or user_input["council"] == "":
                errors["base"] = "council"

            if not errors:
                user_input["council"] = self.council_names[
                    self.council_options.index(user_input["council"])
                ]
                self.data = user_input
                _LOGGER.info(LOG_PREFIX + "User input: %s", user_input)
                return await self.async_step_council()

        _LOGGER.info(
            LOG_PREFIX + "Showing user form with options: %s", self.council_options
        )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("name", default=""): cv.string,
                    vol.Required("council", default=""): vol.In(self.council_options),
                }
            ),
            errors=errors,
        )

    async def async_step_council(self, user_input=None):
        """Second step to configure the council details."""
        errors = {}

        if user_input is not None:
            if "skip_get_url" in self.councils_data[self.data["council"]]:
                user_input["skip_get_url"] = True
                user_input["url"] = self.councils_data[self.data["council"]]["url"]

            user_input["name"] = "{}".format(self.data["name"])
            user_input["council"] = self.data["council"]

            _LOGGER.info(LOG_PREFIX + "Creating config entry with data: %s", user_input)
            return self.async_create_entry(title=user_input["name"], data=user_input)

        council_schema = await self.get_council_schema(self.data["council"])
        _LOGGER.info(
            LOG_PREFIX + "Showing council form with schema: %s", council_schema
        )
        return self.async_show_form(
            step_id="council", data_schema=council_schema, errors=errors
        )

    async def async_step_init(self, user_input=None):
        """Handle a flow initiated by the user."""
        _LOGGER.info(LOG_PREFIX + "Initiating flow with user input: %s", user_input)
        return await self.async_step_user(user_input)

    async def async_step_reconfigure(self, user_input=None):
        """Handle reconfiguration of the integration."""
        self.config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if self.config_entry is None:
            return self.async_abort(reason="reconfigure_failed")

        return await self.async_step_reconfigure_confirm()

    async def async_step_reconfigure_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle a reconfiguration flow initialized by the user."""
        errors: dict[str, str] = {}
        existing_data = self.config_entry.data

        # Load council data and initialize options
        self.councils_data = await self.get_councils_json()
        self.council_names = list(self.councils_data.keys())
        self.council_options = [
            self.councils_data[name]["wiki_name"] for name in self.council_names
        ]

        # Map the stored council key to its corresponding wiki_name
        council_key = existing_data.get("council")
        council_wiki_name = (
            self.councils_data[council_key]["wiki_name"] if council_key else None
        )

        if user_input is not None:
            # Reverse map the selected wiki_name back to the council key
            user_input["council"] = self.council_names[
                self.council_options.index(user_input["council"])
            ]
            # Update the config entry with the new data
            data = {**existing_data, **user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                title=user_input.get("name", self.config_entry.title),
                data=data,
            )
            # Optionally, reload the integration to apply changes
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_abort(reason="Reconfigure Successful")

        # Get the council schema based on the current council setting
        council_schema = await self.get_council_schema(council_key)

        # Track added fields to avoid duplicates
        added_fields = set()

        # Build the schema dynamically based on the existing data and council-specific fields
        schema = vol.Schema(
            {
                vol.Required("name", default=existing_data.get("name", "")): str,
                vol.Required("council", default=council_wiki_name): vol.In(
                    self.council_options
                ),
            }
        )

        added_fields.update(["name", "council"])

        # Include the fields from existing_data that were present in the original config
        if "url" in existing_data:
            schema = schema.extend(
                {vol.Required("url", default=existing_data["url"]): str}
            )
            added_fields.add("url")
        if "uprn" in existing_data:
            schema = schema.extend(
                {vol.Required("uprn", default=existing_data["uprn"]): str}
            )
            added_fields.add("uprn")
        if "postcode" in existing_data:
            schema = schema.extend(
                {vol.Required("postcode", default=existing_data["postcode"]): str}
            )
            added_fields.add("postcode")
        if "number" in existing_data:
            schema = schema.extend(
                {vol.Required("number", default=existing_data["number"]): str}
            )
            added_fields.add("number")
        if "web_driver" in existing_data:
            schema = schema.extend(
                {vol.Optional("web_driver", default=existing_data["web_driver"]): str}
            )
            added_fields.add("web_driver")
            schema = schema.extend(
                {vol.Optional("headless", default=existing_data["headless"]): bool}
            )
            added_fields.add("headless")
            schema = schema.extend(
                {
                    vol.Optional(
                        "local_browser", default=existing_data["local_browser"]
                    ): bool
                }
            )
            added_fields.add("local_browser")

        # Include the fields from existing_data that were present in the original config
        if "timeout" in existing_data:
            schema = schema.extend(
                {vol.Required("timeout", default=existing_data["timeout"]): int}
            )
            added_fields.add("timeout")

        # Add any other fields defined in council_schema that haven't been added yet
        for key, field in council_schema.schema.items():
            if key not in added_fields:
                schema = schema.extend({key: field})

        # Show the form with the dynamically built schema
        return self.async_show_form(
            step_id="reconfigure_confirm",
            data_schema=schema,
            errors=errors,
        )
