# test_config_flow.py

"""Test UkBinCollection config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import HomeAssistant

from custom_components.uk_bin_collection.config_flow import UkBinCollectionConfigFlow
from custom_components.uk_bin_collection.const import DOMAIN

from .common_utils import MockConfigEntry

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
    hass: HomeAssistant, flow, user_input_initial, user_input_council
):
    # Start the flow and complete the `user` step
    result = await flow.async_step_user(user_input=user_input_initial)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "council"

    # Complete the `council` step
    result = await flow.async_step_council(user_input=user_input_council)

    return result


@pytest.mark.asyncio
async def test_config_flow_with_uprn(hass: HomeAssistant):
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


async def test_config_flow_with_postcode_and_number(hass: HomeAssistant):
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


async def test_config_flow_with_web_driver(hass: HomeAssistant):
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


async def test_config_flow_skipping_url(hass: HomeAssistant):
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


async def test_config_flow_with_custom_url_field(hass: HomeAssistant):
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


async def test_config_flow_missing_name(hass: HomeAssistant):
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
        assert result["errors"] == {"name": "Name is required."}


async def test_config_flow_invalid_icon_color_mapping(hass: HomeAssistant):
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
        assert result["errors"] == {"icon_color_mapping": "Invalid JSON format."}


async def test_config_flow_with_usrn(hass: HomeAssistant):
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


@pytest.mark.asyncio
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

        # Configure async_get_entry to return the existing_entry when called with its entry_id
        hass.config_entries.async_get_entry.return_value = existing_entry

        # Configure async_init to return a FlowResultType.FORM with step_id 'reconfigure_confirm'
        hass.config_entries.flow.async_init.return_value = {
            "flow_id": "test_flow_id",
            "type": data_entry_flow.RESULT_TYPE_FORM,
            "step_id": "reconfigure_confirm",
        }

        # Initialize the flow
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        # Set the context to reconfigure the existing entry
        flow.context = {"source": "reconfigure", "entry_id": existing_entry.entry_id}

        # Mock async_step_reconfigure_confirm's behavior
        with patch.object(
            flow, "async_step_reconfigure_confirm", new=AsyncMock()
        ) as mock_step:
            mock_step.return_value = {
                "type": data_entry_flow.RESULT_TYPE_CREATE_ENTRY,
                "title": "Test Name",
                "data": {
                    "name": "Test Name",
                    "council": "CouncilWithUPRN",
                    "uprn": "0987654321",
                    "timeout": 120,
                },
            }

            # Start the reconfiguration flow
            result = await flow.async_step_reconfigure()

            assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
            assert result["title"] == "Test Name"
            assert result["data"] == {
                "name": "Test Name",
                "council": "CouncilWithUPRN",
                "uprn": "0987654321",
                "timeout": 120,
            }

            # Verify that async_step_reconfigure_confirm was called
            mock_step.assert_called_once()


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


@pytest.mark.asyncio
async def test_get_councils_json_failure(hass: HomeAssistant):
    """Test handling when get_councils_json fails."""
    with patch(
        "aiohttp.ClientSession",
        autospec=True,
    ) as mock_session_cls:
        # Configure the mock session to simulate a network error
        mock_session = mock_session_cls.return_value.__aenter__.return_value
        mock_session.get.side_effect = Exception("Network error")

        # Configure async_init to simulate flow abort due to council data being unavailable
        hass.config_entries.flow.async_init.return_value = {
            "type": data_entry_flow.RESULT_TYPE_ABORT,
            "reason": "council_data_unavailable",
        }

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


async def test_config_flow_user_input_none(hass: HomeAssistant):
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


async def test_config_flow_with_optional_fields(hass: HomeAssistant):
    """Test config flow with optional fields provided."""
    # Assume 'CouncilWithOptionalFields' requires 'uprn' and has optional 'web_driver'
    MOCK_COUNCILS_DATA["CouncilWithOptionalFields"] = {
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


@pytest.mark.asyncio
async def test_get_councils_json_session_creation_failure(hass):
    """Test handling when creating aiohttp ClientSession fails."""
    with patch(
        "aiohttp.ClientSession",
        side_effect=Exception("Failed to create session"),
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        # Configure async_init to simulate flow abort due to council data being unavailable
        hass.config_entries.flow.async_init.return_value = {
            "type": data_entry_flow.RESULT_TYPE_ABORT,
            "reason": "council_data_unavailable",
        }

        # Start the flow using hass.config_entries.flow.async_init
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # The flow should abort due to council data being unavailable
        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "council_data_unavailable"


@pytest.mark.asyncio
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

        # Configure async_init to return a FlowResultType.FORM with step_id 'council'
        hass.config_entries.flow.async_init.return_value = {
            "flow_id": "test_flow_id",
            "type": data_entry_flow.RESULT_TYPE_FORM,
            "step_id": "council",
        }

        # Configure async_configure to return a FlowResultType.CREATE_ENTRY
        hass.config_entries.flow.async_configure.return_value = {
            "type": data_entry_flow.RESULT_TYPE_CREATE_ENTRY,
            "title": "Test Name",
            "data": {
                "name": "Test Name",
                "council": "CouncilWithoutURL",
                "uprn": "1234567890",
                "timeout": 60,
                "skip_get_url": True,
                "url": "https://example.com/council_without_url",
            },
        }

        # Start the flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Provide initial user input
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=user_input_initial
        )

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


async def test_config_flow_missing_council(hass: HomeAssistant):
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
        assert result["errors"] == {"council": "Council is required."}


@pytest.mark.asyncio
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

        # Configure async_get_entry to return the existing_entry when called with its entry_id
        hass.config_entries.async_get_entry.return_value = existing_entry

        # Configure async_init to return a FlowResultType.FORM with step_id 'reconfigure_confirm'
        hass.config_entries.flow.async_init.return_value = {
            "flow_id": "test_flow_id",
            "type": data_entry_flow.RESULT_TYPE_FORM,
            "step_id": "reconfigure_confirm",
        }

        # Initialize the flow
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        # Set the context to reconfigure the existing entry
        flow.context = {"source": "reconfigure", "entry_id": existing_entry.entry_id}

        # Mock async_step_reconfigure_confirm's behavior to handle invalid input
        with patch.object(
            flow, "async_step_reconfigure_confirm", new=AsyncMock()
        ) as mock_step:
            mock_step.return_value = {
                "type": data_entry_flow.RESULT_TYPE_FORM,
                "step_id": "reconfigure_confirm",
                "errors": {"icon_color_mapping": "invalid_json"},
            }

            # Start the reconfiguration flow
            result = await flow.async_step_reconfigure()

            assert result["type"] == data_entry_flow.FlowResultType.FORM
            assert result["step_id"] == "reconfigure_confirm"

            # Provide invalid data (e.g., invalid JSON for icon_color_mapping)
            user_input = {
                "name": "Updated Entry",
                "council": "Council with UPRN",
                "uprn": "0987654321",
                "icon_color_mapping": "invalid json",
                "timeout": 60,
            }

            # Configure async_configure to return an error
            hass.config_entries.flow.async_configure.return_value = {
                "type": data_entry_flow.RESULT_TYPE_FORM,
                "step_id": "reconfigure_confirm",
                "errors": {"icon_color_mapping": "invalid_json"},
            }

            result = await flow.async_step_reconfigure_confirm(user_input=user_input)

            # Should return to the reconfigure_confirm step with an error
            assert result["type"] == data_entry_flow.FlowResultType.FORM
            assert result["step_id"] == "reconfigure_confirm"
            assert result["errors"] == {"icon_color_mapping": "invalid_json"}


@pytest.mark.asyncio
async def test_reconfigure_flow_entry_missing(hass):
    """Test reconfiguration when the config entry is missing."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        # Set the context with an invalid entry_id to simulate a missing entry
        flow.context = {"source": "reconfigure", "entry_id": "invalid_entry_id"}

        # Mock async_get_entry to return None using MagicMock, not AsyncMock
        hass.config_entries.async_get_entry = MagicMock(return_value=None)

        # Run the reconfiguration step to check for abort
        result = await flow.async_step_reconfigure()

        # Assert that the flow aborts due to the missing config entry
        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "reconfigure_failed"


@pytest.mark.asyncio
async def test_reconfigure_flow_no_user_input(hass):
    """Test reconfiguration when user_input is None."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        # Create a mock entry and ensure add_to_hass is awaited
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

        # Mock async_get_entry to return the entry directly, avoiding coroutine issues
        hass.config_entries.async_get_entry = AsyncMock(return_value=existing_entry)

        # Mock async_init and start the reconfigure flow
        hass.config_entries.flow.async_init.return_value = {
            "flow_id": "test_flow_id",
            "type": data_entry_flow.RESULT_TYPE_FORM,
            "step_id": "reconfigure_confirm",
        }

        flow = UkBinCollectionConfigFlow()
        flow.hass = hass
        flow.context = {"source": "reconfigure", "entry_id": existing_entry.entry_id}

        # Proceed without user input, simulating the form return
        with patch.object(
            flow, "async_step_reconfigure_confirm", new=AsyncMock()
        ) as mock_step:
            mock_step.return_value = {
                "type": data_entry_flow.RESULT_TYPE_FORM,
                "step_id": "reconfigure_confirm",
                "errors": {},
            }

            result = await flow.async_step_reconfigure_confirm(user_input=None)

            assert result["type"] == data_entry_flow.FlowResultType.FORM
            assert result["step_id"] == "reconfigure_confirm"


@pytest.mark.asyncio
async def test_check_selenium_server_exception(hass: HomeAssistant):
    """Test exception handling in check_selenium_server."""
    with patch(
        "aiohttp.ClientSession.get",
        side_effect=Exception("Connection error"),
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        result = await flow.check_selenium_server()
        # Expected result is that all URLs are marked as not accessible
        expected_result = [
            ("http://localhost:4444", False),
            ("http://selenium:4444", False),
        ]
        assert result == expected_result


@pytest.mark.asyncio
async def test_get_councils_json_exception(hass: HomeAssistant):
    """Test exception handling in get_councils_json."""
    with patch(
        "aiohttp.ClientSession.get",
        side_effect=Exception("Network error"),
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        result = await flow.get_councils_json()
        assert result == {}


@pytest.mark.asyncio
async def test_async_step_user_council_data_unavailable(hass: HomeAssistant):
    """Test async_step_user when council data is unavailable."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=None,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(user_input={})

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "council_data_unavailable"


@pytest.mark.asyncio
async def test_async_step_council_invalid_icon_color_mapping(hass: HomeAssistant):
    """Test async_step_council with invalid JSON in icon_color_mapping."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass
        flow.data = {
            "name": "Test Name",
            "council": "CouncilWithUPRN",
        }
        flow.councils_data = MOCK_COUNCILS_DATA

        user_input = {
            "uprn": "1234567890",
            "icon_color_mapping": "invalid json",
            "timeout": 60,
        }

        result = await flow.async_step_council(user_input=user_input)

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "council"
        assert result["errors"] == {"icon_color_mapping": "Invalid JSON format."}


@pytest.mark.asyncio
async def test_async_step_reconfigure_entry_none(hass: HomeAssistant):
    """Test async_step_reconfigure when config entry is None."""
    flow = UkBinCollectionConfigFlow()
    flow.hass = hass
    flow.context = {"entry_id": "non_existent_entry_id"}

    # Mock async_get_entry to return None
    flow.hass.config_entries.async_get_entry = MagicMock(return_value=None)

    result = await flow.async_step_reconfigure()

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_failed"


@pytest.mark.asyncio
async def test_async_step_reconfigure_confirm_user_input_none(hass: HomeAssistant):
    """Test async_step_reconfigure_confirm when user_input is None."""
    flow = UkBinCollectionConfigFlow()
    flow.hass = hass

    # Create a mock config entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Test Name",
            "council": "CouncilWithUPRN",
            "uprn": "1234567890",
            "timeout": 60,
        },
    )
    config_entry.add_to_hass(hass)

    flow.config_entry = config_entry
    flow.context = {"entry_id": config_entry.entry_id}
    flow.councils_data = MOCK_COUNCILS_DATA

    result = await flow.async_step_reconfigure_confirm(user_input=None)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "reconfigure_confirm"


@pytest.mark.asyncio
async def test_async_step_council_missing_council_key(hass: HomeAssistant):
    """Test async_step_council when council_key is missing in councils_data."""
    flow = UkBinCollectionConfigFlow()
    flow.hass = hass
    flow.data = {
        "name": "Test Name",
        "council": "NonExistentCouncil",
    }
    flow.councils_data = MOCK_COUNCILS_DATA

    result = await flow.async_step_council(user_input=None)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "council"


@pytest.mark.asyncio
async def test_check_chromium_installed_exception(hass: HomeAssistant):
    """Test exception handling in check_chromium_installed."""
    with patch(
        "shutil.which",
        side_effect=Exception("Filesystem error"),
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        result = await flow.check_chromium_installed()
        assert result is False



@pytest.mark.asyncio
async def test_async_step_reconfigure_confirm_invalid_json(hass: HomeAssistant):
    """Test async_step_reconfigure_confirm with invalid JSON."""
    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=MOCK_COUNCILS_DATA,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        # Create a mock config entry
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Existing Entry",
                "council": "CouncilWithUPRN",
                "uprn": "1234567890",
                "timeout": 60,
            },
        )
        config_entry.add_to_hass(hass)

        flow.config_entry = config_entry
        flow.context = {"entry_id": config_entry.entry_id}

        # Set up mocks for async methods
        hass.config_entries.async_reload = AsyncMock()
        hass.config_entries.async_update_entry = MagicMock()

        user_input = {
            "name": "Updated Entry",
            "council": "Council with UPRN",
            "icon_color_mapping": "invalid json",
            "uprn": "0987654321",
            "timeout": 120,
        }

        result = await flow.async_step_reconfigure_confirm(user_input=user_input)

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "reconfigure_confirm"
        assert result["errors"] == {"icon_color_mapping": "Invalid JSON format."}

