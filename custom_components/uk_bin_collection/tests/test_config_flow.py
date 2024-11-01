# test_config_flow.py

"""Test UkBinCollection config flow."""
from unittest.mock import patch
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_NAME, CONF_URL
from pytest_homeassistant_custom_component.common import MockConfigEntry
import pytest
import voluptuous as vol

from custom_components.uk_bin_collection.config_flow import (
    UkBinCollectionConfigFlow,
)
from custom_components.uk_bin_collection.const import DOMAIN


# Fixture to enable custom integrations
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield

# Mock council data representing different scenarios
MOCK_COUNCILS_DATA = {
    "CouncilWithoutURL": {
        "wiki_name": "Council without URL",
        "skip_get_url": True,
        # Do not include 'custom_component_show_url_field'
        # Other necessary fields
        "uprn": True,
        "url": "https://example.com/council_without_url",
    },
    "CouncilWithUSRN": {
        "wiki_name": "Council with USRN",
        "usrn": True,
    },
    "CouncilWithUPRN": {
        "wiki_name": "Council with UPRN",
        "uprn": True,
    },
    "CouncilWithPostcodeNumber": {
        "wiki_name": "Council with Postcode and Number",
        "postcode": True,
        "house_number": True,
    },
    "CouncilWithWebDriver": {
        "wiki_name": "Council with Web Driver",
        "web_driver": True,
    },
    "CouncilSkippingURL": {
        "wiki_name": "Council skipping URL",
        "skip_get_url": True,
        "url": "https://council.example.com",
    },
    "CouncilCustomURLField": {
        "wiki_name": "Council with Custom URL Field",
        "custom_component_show_url_field": True,
    },
    # Add more mock councils as needed to cover different scenarios
}

# Helper function to initiate the config flow and proceed through steps
async def proceed_through_config_flow(
    hass, flow, user_input_initial, user_input_council
):
    # Start the flow and complete the `user` step
    result = await flow.async_step_user(user_input=user_input_initial)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "council"

    # Complete the `council` step
    result = await flow.async_step_council(user_input=user_input_council)

    return result

async def test_config_flow_with_uprn(hass):
    """Test config flow for a council requiring UPRN."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        user_input_initial = {
            "name": "Test Name",
            "council": "Council with UPRN",
        }
        user_input_council = {
            "uprn": "1234567890",
            "timeout": 60,
        }

        result = await proceed_through_config_flow(
            hass, flow, user_input_initial, user_input_council
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Name"
        assert result["data"] == {
            "name": "Test Name",
            "council": "CouncilWithUPRN",
            "uprn": "1234567890",
            "timeout": 60,
        }

async def test_config_flow_with_postcode_and_number(hass):
    """Test config flow for a council requiring postcode and house number."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        user_input_initial = {
            "name": "Test Name",
            "council": "Council with Postcode and Number",
        }
        user_input_council = {
            "postcode": "AB1 2CD",
            "number": "42",
            "timeout": 60,
        }

        result = await proceed_through_config_flow(
            hass, flow, user_input_initial, user_input_council
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Name"
        assert result["data"] == {
            "name": "Test Name",
            "council": "CouncilWithPostcodeNumber",
            "postcode": "AB1 2CD",
            "number": "42",
            "timeout": 60,
        }

async def test_config_flow_with_web_driver(hass):
    """Test config flow for a council requiring web driver."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        user_input_initial = {
            "name": "Test Name",
            "council": "Council with Web Driver",
        }
        user_input_council = {
            "web_driver": "/path/to/webdriver",
            "headless": True,
            "local_browser": False,
            "timeout": 60,
        }

        result = await proceed_through_config_flow(
            hass, flow, user_input_initial, user_input_council
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Name"
        assert result["data"] == {
            "name": "Test Name",
            "council": "CouncilWithWebDriver",
            "web_driver": "/path/to/webdriver",
            "headless": True,
            "local_browser": False,
            "timeout": 60,
        }

async def test_config_flow_skipping_url(hass):
    """Test config flow for a council that skips URL input."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        user_input_initial = {
            "name": "Test Name",
            "council": "Council skipping URL",
        }
        user_input_council = {
            "timeout": 60,
        }

        result = await proceed_through_config_flow(
            hass, flow, user_input_initial, user_input_council
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Name"
        assert result["data"] == {
            "name": "Test Name",
            "council": "CouncilSkippingURL",
            "skip_get_url": True,
            "url": "https://council.example.com",
            "timeout": 60,
        }

async def test_config_flow_with_custom_url_field(hass):
    """Test config flow for a council with custom URL field."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        user_input_initial = {
            "name": "Test Name",
            "council": "Council with Custom URL Field",
        }
        user_input_council = {
            "url": "https://custom-url.example.com",
            "timeout": 60,
        }

        result = await proceed_through_config_flow(
            hass, flow, user_input_initial, user_input_council
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Name"
        assert result["data"] == {
            "name": "Test Name",
            "council": "CouncilCustomURLField",
            "url": "https://custom-url.example.com",
            "timeout": 60,
        }

async def test_config_flow_missing_name(hass):
    """Test config flow when name is missing."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        user_input_initial = {
            "name": "",  # Missing name
            "council": "Council with UPRN",
        }

        result = await flow.async_step_user(user_input=user_input_initial)

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "name"}

async def test_config_flow_invalid_icon_color_mapping(hass):
    """Test config flow with invalid icon_color_mapping JSON."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        user_input_initial = {
            "name": "Test Name",
            "council": "Council with UPRN",
            "icon_color_mapping": "invalid json",  # Invalid JSON
        }

        result = await flow.async_step_user(user_input=user_input_initial)

        # Should return to the user step with an error
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"icon_color_mapping": "invalid_json"}

async def test_config_flow_with_usrn(hass):
    """Test config flow for a council requiring USRN."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        user_input_initial = {
            "name": "Test Name",
            "council": "Council with USRN",
        }
        user_input_council = {
            "usrn": "9876543210",
            "timeout": 60,
        }

        result = await proceed_through_config_flow(
            hass, flow, user_input_initial, user_input_council
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Name"
        assert result["data"] == {
            "name": "Test Name",
            "council": "CouncilWithUSRN",
            "usrn": "9876543210",
            "timeout": 60,
        }

async def test_reconfigure_flow(hass):
    """Test reconfiguration of an existing integration."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        # Create an existing entry
        existing_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Existing Entry",
                "council": "CouncilWithUPRN",
                "uprn": "1234567890",
                "timeout": 60,
            },
        )
        existing_entry.add_to_hass(hass)

        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        # Set the context to reconfigure the existing entry
        flow.context = {"source": "reconfigure", "entry_id": existing_entry.entry_id}

        # Start the reconfiguration flow
        result = await flow.async_step_reconfigure()

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "reconfigure_confirm"

        # Provide updated data
        user_input = {
            "name": "Updated Entry",
            "council": "Council with UPRN",
            "uprn": "0987654321",
            "timeout": 120,
        }

        with patch(
            "homeassistant.config_entries.ConfigEntries.async_reload",
            return_value=True,
        ) as mock_reload:
            result = await flow.async_step_reconfigure_confirm(user_input=user_input)
            mock_reload.assert_called_once_with(existing_entry.entry_id)

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "Reconfigure Successful"

        # Verify that the existing entry has been updated
        assert existing_entry.data["name"] == "Updated Entry"
        assert existing_entry.data["uprn"] == "0987654321"
        assert existing_entry.data["timeout"] == 120


async def get_councils_json(self) -> object:
    """Returns an object of supported councils and their required fields."""
    url = "https://raw.githubusercontent.com/robbrad/UKBinCollectionData/0.104.0/uk_bin_collection/tests/input.json"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data_text = await response.text()
                return json.loads(data_text)
    except Exception as e:
        _LOGGER.error("Failed to fetch councils data: %s", e)
        return {}


async def test_get_councils_json_failure(hass):
    """Test handling when get_councils_json fails."""
    with patch(
        "aiohttp.ClientSession",
        autospec=True,
    ) as mock_session_cls:
        # Configure the mock session to simulate a network error
        mock_session = mock_session_cls.return_value.__aenter__.return_value
        mock_session.get.side_effect = Exception("Network error")

        # Initialize the flow
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        # Start the flow using hass.config_entries.flow.async_init
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # The flow should abort due to council data being unavailable
        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "council_data_unavailable"



async def test_async_step_init(hass):
    """Test the initial step of the flow."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.async_step_user",
        return_value=data_entry_flow.FlowResultType.FORM,
    ) as mock_async_step_user:
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        result = await flow.async_step_init(user_input=None)
        mock_async_step_user.assert_called_once_with(user_input=None)
        assert result == data_entry_flow.FlowResultType.FORM

async def test_config_flow_user_input_none(hass):
    """Test config flow when user_input is None."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(user_input=None)

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"

async def test_config_flow_with_optional_fields(hass):
    """Test config flow with optional fields provided."""
    # Assume 'CouncilWithOptionalFields' requires 'uprn' and has optional 'web_driver'
    MOCK_COUNCILS_DATA['CouncilWithOptionalFields'] = {
        "wiki_name": "Council with Optional Fields",
        "uprn": True,
        "web_driver": True,
    }

    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        user_input_initial = {
            "name": "Test Name",
            "council": "Council with Optional Fields",
        }
        user_input_council = {
            "uprn": "1234567890",
            "web_driver": "/path/to/webdriver",
            "headless": True,
            "local_browser": False,
            "timeout": 60,
        }

        result = await proceed_through_config_flow(
            hass, flow, user_input_initial, user_input_council
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Name"
        assert result["data"] == {
            "name": "Test Name",
            "council": "CouncilWithOptionalFields",
            "uprn": "1234567890",
            "web_driver": "/path/to/webdriver",
            "headless": True,
            "local_browser": False,
            "timeout": 60,
        }

async def test_get_councils_json_session_creation_failure(hass):
    """Test handling when creating aiohttp ClientSession fails."""
    with patch(
        "aiohttp.ClientSession",
        side_effect=Exception("Failed to create session"),
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        # Start the flow using hass.config_entries.flow.async_init
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # The flow should abort due to council data being unavailable
        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "council_data_unavailable"

async def test_config_flow_council_without_url(hass):
    """Test config flow for a council where 'url' field should not be included."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        user_input_initial = {
            "name": "Test Name",
            "council": "Council without URL",
        }
        user_input_council = {
            "uprn": "1234567890",
            "timeout": 60,
        }

        # Start the flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Provide initial user input
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=user_input_initial
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "council"

        # Check that 'url' is not in the schema
        schema_fields = result["data_schema"].schema
        assert "url" not in schema_fields

        # Provide council-specific input
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=user_input_council
        )

        # Flow should proceed to create entry
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Name"
        assert result["data"] == {
            "name": "Test Name",
            "council": "CouncilWithoutURL",
            "uprn": "1234567890",
            "timeout": 60,
            "skip_get_url": True,
            "url": "https://example.com/council_without_url",
        }
async def test_config_flow_missing_council(hass):
    """Test config flow when council is missing."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        user_input_initial = {
            "name": "Test Name",
            "council": "",  # Missing council
        }

        result = await flow.async_step_user(user_input=user_input_initial)

        # Should return to the user step with an error
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "council"}

async def test_reconfigure_flow_with_errors(hass):
    """Test reconfiguration with invalid input."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        # Create an existing entry
        existing_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Existing Entry",
                "council": "CouncilWithUPRN",
                "uprn": "1234567890",
                "timeout": 60,
            },
        )
        existing_entry.add_to_hass(hass)

        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        # Set the context to reconfigure the existing entry
        flow.context = {"source": "reconfigure", "entry_id": existing_entry.entry_id}

        # Start the reconfiguration flow
        result = await flow.async_step_reconfigure()

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "reconfigure_confirm"

        # Provide invalid data (e.g., invalid JSON for icon_color_mapping)
        user_input = {
            "name": "Updated Entry",
            "council": "Council with UPRN",
            "uprn": "0987654321",
            "icon_color_mapping": "invalid json",
            "timeout": 60,
        }

        result = await flow.async_step_reconfigure_confirm(user_input=user_input)

        # Should return to the reconfigure_confirm step with an error
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "reconfigure_confirm"
        assert result["errors"] == {"icon_color_mapping": "invalid_json"}

async def test_reconfigure_flow_entry_missing(hass):
    """Test reconfiguration when the config entry is missing."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        # Set the context with an invalid entry_id
        flow.context = {"source": "reconfigure", "entry_id": "invalid_entry_id"}

        # Start the reconfiguration flow
        result = await flow.async_step_reconfigure()

        # Flow should abort due to missing config entry
        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "reconfigure_failed"

async def test_reconfigure_flow_no_user_input(hass):
    """Test reconfiguration when user_input is None."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        # Create an existing entry
        existing_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Existing Entry",
                "council": "CouncilWithUPRN",
                "uprn": "1234567890",
                "timeout": 60,
            },
        )
        existing_entry.add_to_hass(hass)

        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        # Set the context to reconfigure the existing entry
        flow.context = {"source": "reconfigure", "entry_id": existing_entry.entry_id}

        # Start the reconfiguration flow
        result = await flow.async_step_reconfigure()

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "reconfigure_confirm"

        # Proceed without user input
        result = await flow.async_step_reconfigure_confirm(user_input=None)

        # Should show the form again
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "reconfigure_confirm"
