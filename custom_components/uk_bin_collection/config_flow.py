import aiohttp
import json
import voluptuous as vol
from homeassistant import config_entries, core

DOMAIN = "uk_bin_collection"

DATA_SCHEMA = vol.Schema(
    {
        vol.Required("url", default=""): str,
        vol.Required("council", default=""): str,
        vol.Optional("uprn", default=""): str,
        vol.Optional("postcode", default=""): str,
        vol.Optional("house_number", default=""): str,
        vol.Optional("usrn", default=""): str,
        vol.Optional("SKIP_GET_URL", default=""): str,
    }
)

class UkBinCollectionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Perform validation and setup here based on user_input
            # For example, check if the API URL and council name are provided

            # If the validation is successful, create the config entry
            return self.async_create_entry(title="UK Bin Collection", data=user_input)

        # Fetch the JSON data from the provided URL
        url = "https://raw.githubusercontent.com/robbrad/UKBinCollectionData/master/uk_bin_collection/tests/input.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data_text = await response.text()
                data = json.loads(data_text)

        # Extract council names and create a list of options for the dropdown
        council_names = list(data.keys())
        council_options = {name: data[name]["wiki_name"] for name in council_names}

        # Show the configuration form to the user with the dropdown for the "council" field
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
            description_placeholders=council_options,
        )

    async def async_step_init(self, user_input=None):
        """Handle a flow initiated by the user."""
        return await self.async_step_user(user_input)
