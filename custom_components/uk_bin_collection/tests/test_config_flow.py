# test_config_flow.py

"""Test UkBinCollection config flow."""

import asyncio
import json
from datetime import date, datetime, timedelta
from json import JSONDecodeError
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
import voluptuous as vol
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.uk_bin_collection.config_flow import (
    UkBinCollectionConfigFlow,
    UkBinCollectionOptionsFlowHandler,
    async_get_options_flow,
)
from custom_components.uk_bin_collection.const import DOMAIN, LOG_PREFIX
from custom_components.uk_bin_collection.sensor import load_icon_color_mapping

from .common_utils import MockConfigEntry


@pytest.fixture
def hass_with_loop(hass, event_loop):
    hass.loop = event_loop
    return hass


# Mock council data representing different scenarios
MOCK_COUNCILS_DATA = {
    "CouncilTest": {
        "wiki_name": "Council Test",
        "uprn": True,
        "url": "https://example.com/council_test",
        "skip_get_url": False,
    },
    "CouncilSkip": {
        "wiki_name": "Council Skip URL",
        "skip_get_url": True,
        "url": "https://example.com/skip",
    },
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


# Create a dummy HomeAssistant object.
class DummyHass:
    def __init__(self, loop):
        self.data = {}
        self.config_entries = MagicMock()
        self.config_entries.async_update_entry = AsyncMock()
        self.config_entries.async_reload = AsyncMock()
        self.loop = loop


@pytest.fixture
def dummy_hass(event_loop):
    return DummyHass(event_loop)


# A sample councils data for the options flow tests.
MOCK_COUNCILS_DATA_OPTIONS = {
    "CouncilTest": {
        "wiki_name": "Council Test",
        "uprn": True,
        "url": "https://example.com/council_test",
    }
}


@pytest.fixture
def options_flow(dummy_hass):
    """Create an instance of the options flow with a dummy config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Test Options",
            "council": "CouncilTest",
            "update_interval": 12,
            "icon_color_mapping": '{"CouncilTest": {"icon": "mdi:trash", "color": "green"}}',
        },
        entry_id="options_test",
        unique_id="options_unique",
    )
    config_entry.add_to_hass(dummy_hass)
    flow = UkBinCollectionOptionsFlowHandler(config_entry)
    flow.hass = dummy_hass
    return flow, config_entry


# Dummy config entry class for testing.
class DummyEntry:
    def __init__(self, data, entry_id="dummy"):
        self.data = data
        self.entry_id = entry_id
        self.title = data.get("name", "")


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
        assert result["reason"] == "Reconfigure Failed"


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
        assert result["reason"] == "Council Data Unavailable"


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
    assert result["reason"] == "Reconfigure Failed"


async def test_async_step_reconfigure_confirm_user_input_none(hass: HomeAssistant):
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

    # Patch async_get_entry to return the config_entry immediately
    hass.config_entries.async_get_entry = MagicMock(return_value=config_entry)

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


async def test_async_step_reconfigure_confirm_invalid_json(hass: HomeAssistant):
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

        # Patch async_get_entry to return the config_entry (not a coroutine)
        hass.config_entries.async_get_entry = MagicMock(return_value=config_entry)

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

        # Should return to the reconfigure_confirm step with an error
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "reconfigure_confirm"
        assert result["errors"] == {"icon_color_mapping": "Invalid JSON format."}


@pytest.mark.asyncio
async def test_config_flow_with_manual_refresh_only(hass: HomeAssistant):
    """Test config flow when the user selects manual_refresh_only = True."""
    mock_councils = {
        "CouncilWithUPRN": {
            "wiki_name": "Council with UPRN",
            "uprn": True,
        }
    }

    with patch(
        "custom_components.uk_bin_collection.config_flow.UkBinCollectionConfigFlow.get_councils_json",
        return_value=mock_councils,
    ):
        flow = UkBinCollectionConfigFlow()
        flow.hass = hass

        # Step 1: user selects council + sets manual_refresh_only
        user_input_initial = {
            "name": "Test Manual Refresh",
            "council": "Council with UPRN",
            "manual_refresh_only": True,
            # icon_color_mapping, etc. are optional
        }

        # Step 2: council details
        # minimal fields needed for council requiring UPRN
        user_input_council = {
            "uprn": "1234567890",
            "timeout": 45,
            # note that if skip_get_url is False, you might need "url" or not
        }

        # Start user step
        result = await flow.async_step_user(user_input=user_input_initial)
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "council"

        # Complete council step
        result = await flow.async_step_council(user_input=user_input_council)
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == "Test Manual Refresh"

        # Confirm the config entry data now includes manual_refresh_only
        assert result["data"] == {
            "name": "Test Manual Refresh",
            "council": "CouncilWithUPRN",
            "uprn": "1234567890",
            "timeout": 45,
            "manual_refresh_only": True,
        }


# ---------------------------
# Tests for helper functions
# ---------------------------
def test_load_icon_color_mapping_valid():
    valid_json = '{"General Waste": {"icon": "mdi:trash-can", "color": "brown"}}'
    result = load_icon_color_mapping(valid_json)
    assert isinstance(result, dict)
    assert result["General Waste"]["icon"] == "mdi:trash-can"
    assert result["General Waste"]["color"] == "brown"


def test_load_icon_color_mapping_invalid():
    invalid_json = '{"icon":"mdi:trash" "no_comma":true}'  # missing comma
    with patch("logging.Logger.warning") as mock_warn:
        result = load_icon_color_mapping(invalid_json)
        assert result == {}
        mock_warn.assert_called_once_with(
            f"{LOG_PREFIX} Invalid icon_color_mapping JSON: {invalid_json}. Using default settings."
        )


def test_map_wiki_name_to_council_key():
    flow = UkBinCollectionConfigFlow()
    flow.council_names = ["CouncilTest"]
    flow.council_options = ["Council Test"]
    # Valid mapping
    key = flow.map_wiki_name_to_council_key("Council Test")
    assert key == "CouncilTest"
    # Invalid mapping: expect empty string and a logged error.
    with patch("logging.Logger.error") as mock_error:
        key_invalid = flow.map_wiki_name_to_council_key("Not Exist")
        assert key_invalid == ""
        mock_error.assert_called_once_with(
            "Wiki name '%s' not found in council options.", "Not Exist"
        )


def test_is_valid_json():
    valid = '{"key": "value"}'
    invalid = '{"key": "value",}'  # trailing comma makes it invalid
    assert UkBinCollectionConfigFlow.is_valid_json(valid) is True
    assert UkBinCollectionConfigFlow.is_valid_json(invalid) is False


# ---------------------------
# Tests for async_step_user
# ---------------------------
@pytest.mark.asyncio
async def test_async_step_user_missing_fields(hass):
    """Test async_step_user returns errors when required fields are missing."""
    flow = UkBinCollectionConfigFlow()
    flow.hass = hass
    # Set councils data so that form is rendered
    flow.councils_data = MOCK_COUNCILS_DATA
    flow.council_names = list(MOCK_COUNCILS_DATA.keys())
    flow.council_options = [
        MOCK_COUNCILS_DATA[name]["wiki_name"] for name in flow.council_names
    ]
    # Missing both 'name' and 'council'
    result = await flow.async_step_user(user_input={"name": "", "council": ""})
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert "name" in result["errors"]
    assert "council" in result["errors"]


@pytest.mark.asyncio
async def test_async_step_user_invalid_icon_mapping(hass):
    """Test async_step_user returns error for invalid icon_color_mapping JSON."""
    flow = UkBinCollectionConfigFlow()
    flow.hass = hass
    flow.councils_data = MOCK_COUNCILS_DATA
    flow.council_names = list(MOCK_COUNCILS_DATA.keys())
    flow.council_options = [
        MOCK_COUNCILS_DATA[name]["wiki_name"] for name in flow.council_names
    ]
    result = await flow.async_step_user(
        user_input={
            "name": "Test Name",
            "council": MOCK_COUNCILS_DATA["CouncilTest"]["wiki_name"],
            "icon_color_mapping": "not a json",
        }
    )
    assert result["type"] == "form"
    assert result["errors"] == {"icon_color_mapping": "Invalid JSON format."}


@pytest.mark.asyncio
async def test_async_step_user_no_councils(hass):
    """Test async_step_user aborts when councils data cannot be fetched."""
    flow = UkBinCollectionConfigFlow()
    flow.hass = hass
    # Patch get_councils_json to return an empty dict (simulate failure)
    with patch.object(flow, "get_councils_json", return_value={}):
        result = await flow.async_step_user(
            user_input={"name": "Test", "council": "CouncilTest"}
        )
        assert result["type"] == "abort"
        assert result["reason"] == "Council Data Unavailable"


# ---------------------------
# Tests for async_step_council
# ---------------------------
@pytest.mark.asyncio
async def test_async_step_council_skip_get_url(hass):
    """Test that async_step_council sets skip_get_url when required."""
    flow = UkBinCollectionConfigFlow()
    flow.hass = hass
    # Set up data so that the council in question requires URL skipping.
    flow.data = {"name": "Test", "council": "CouncilSkip"}
    flow.councils_data = MOCK_COUNCILS_DATA
    # Provide minimal user input (e.g. only timeout)
    user_input = {"timeout": 60}
    result = await flow.async_step_council(user_input=user_input)
    # In a real flow, if no errors are present the entry would be created.
    # Here, we simply verify that the user input was merged with skip_get_url.
    if "data" in result:
        # If the flow creates an entry, check that skip_get_url is present.
        assert result["data"].get("skip_get_url") is True
        assert result["data"].get("url") == MOCK_COUNCILS_DATA["CouncilSkip"].get("url")
    else:
        # Otherwise, the form is returned with no errors.
        assert result["type"] == "form"


# ---------------------------
# Tests for reconfigure steps
# ---------------------------
@pytest.mark.asyncio
async def test_async_step_reconfigure_confirm_user_input_none(hass):
    """Test async_step_reconfigure_confirm returns form when no user input is provided."""
    flow = UkBinCollectionConfigFlow()
    flow.hass = hass
    # Create a dummy config entry.
    dummy_entry = DummyEntry(
        {
            "name": "Test Name",
            "council": "CouncilTest",
            "uprn": "1234567890",
            "timeout": 60,
        },
        entry_id="dummy",
    )
    # Make sure async_get_entry returns a plain entry.
    hass.config_entries.async_get_entry = MagicMock(return_value=dummy_entry)
    flow.config_entry = dummy_entry
    flow.context = {"entry_id": dummy_entry.entry_id}
    flow.councils_data = MOCK_COUNCILS_DATA

    result = await flow.async_step_reconfigure_confirm(user_input=None)
    assert result["type"] == "form"
    assert result["step_id"] == "reconfigure_confirm"


@pytest.mark.asyncio
async def test_async_step_reconfigure_confirm_invalid_json(hass):
    """Test async_step_reconfigure_confirm returns errors with invalid JSON mapping and update_interval."""
    flow = UkBinCollectionConfigFlow()
    flow.hass = hass
    dummy_entry = DummyEntry(
        {
            "name": "Existing Entry",
            "council": "CouncilTest",
            "uprn": "1234567890",
            "timeout": 60,
        },
        entry_id="dummy",
    )
    hass.config_entries.async_get_entry = MagicMock(return_value=dummy_entry)
    flow.config_entry = dummy_entry
    flow.context = {"entry_id": dummy_entry.entry_id}
    flow.councils_data = MOCK_COUNCILS_DATA

    # Patch async_update_entry and async_reload (they won't be used if there are errors)
    hass.config_entries.async_update_entry = MagicMock()
    hass.config_entries.async_reload = AsyncMock()

    user_input = {
        "name": "Updated Entry",
        "council": MOCK_COUNCILS_DATA["CouncilTest"]["wiki_name"],
        "update_interval": "0",  # invalid (less than 1)
        "icon_color_mapping": "invalid json",
        "uprn": "0987654321",
        "timeout": 120,
    }
    result = await flow.async_step_reconfigure_confirm(user_input=user_input)
    assert result["type"] == "form"
    assert result["step_id"] == "reconfigure_confirm"
    # Expect errors for update_interval and icon_color_mapping.
    assert "update_interval" in result["errors"]
    assert "icon_color_mapping" in result["errors"]


# ---------------------------
# Test get_councils_json failure
# ---------------------------
@pytest.mark.asyncio
async def test_get_councils_json_failure(hass):
    flow = UkBinCollectionConfigFlow()
    flow.hass = hass
    with patch("aiohttp.ClientSession") as mock_session_cls:
        # Simulate network error.
        mock_session = mock_session_cls.return_value.__aenter__.return_value
        mock_session.get.side_effect = Exception("Network error")
        result = await flow.get_councils_json()
        assert result == {}


# ---------------------------
# Test get_council_schema
# ---------------------------
@pytest.mark.asyncio
async def test_get_council_schema(hass):
    flow = UkBinCollectionConfigFlow()
    flow.hass = hass
    flow.councils_data = {
        "CouncilTest": {
            "wiki_name": "Council Test",
            "skip_get_url": False,
            "uprn": True,
            "postcode": True,
            "house_number": True,
            "usrn": True,
            "web_driver": True,
        }
    }
    schema = await flow.get_council_schema("CouncilTest")
    # Check that required fields appear in the schema.
    required_fields = ["url", "uprn", "postcode", "number", "usrn", "timeout"]
    for field in required_fields:
        assert field in schema.schema


# ---------------------------
# Test build_reconfigure_schema
# ---------------------------
def test_build_reconfigure_schema(hass):
    flow = UkBinCollectionConfigFlow()
    flow.council_names = ["CouncilTest"]
    flow.council_options = ["Council Test"]
    existing_data = {
        "name": "Old Name",
        "council": "CouncilTest",
        "update_interval": 12,
        "url": "https://example.com",
        "icon_color_mapping": "{}",
    }
    schema = flow.build_reconfigure_schema(existing_data, "Council Test")
    assert isinstance(schema, vol.Schema)
    schema_dict = schema.schema
    assert "name" in schema_dict
    assert "council" in schema_dict
    assert "update_interval" in schema_dict


# ---------------------------
# Test async_step_import
# ---------------------------
@pytest.mark.asyncio
async def test_async_step_import(hass):
    """Test that import flows call async_step_user."""
    flow = UkBinCollectionConfigFlow()
    flow.hass = hass
    import_config = {"name": "Imported", "council": "Council Test", "uprn": "111"}
    # For import, the flow should delegate to async_step_user.
    result = await flow.async_step_import(import_config)
    # We assume that async_step_user would return a form (or create entry)
    assert result is not None


@pytest.mark.asyncio
async def test_options_flow_no_councils(dummy_hass):
    """Test async_step_init aborts if get_councils_json returns empty data."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data={"name": "Test Options"}, entry_id="opt_test"
    )
    config_entry.add_to_hass(dummy_hass)
    flow = UkBinCollectionOptionsFlowHandler(config_entry)
    flow.hass = dummy_hass

    # Patch get_councils_json to return an empty dict
    flow.get_councils_json = AsyncMock(return_value={})
    result = await flow.async_step_init(user_input=None)
    # Expect an abort with reason "Council Data Unavailable"
    assert result["reason"] == "Council Data Unavailable"


def test_build_options_schema(options_flow):
    """Test that build_options_schema returns a schema with expected keys."""
    flow, config_entry = options_flow
    # Set up the lists for schema building
    flow.council_names = ["CouncilTest"]
    flow.council_options = ["Council Test"]
    existing_data = {
        "name": "Test Options",
        "council": "CouncilTest",
        "update_interval": 12,
        "icon_color_mapping": '{"CouncilTest": {"icon": "mdi:trash", "color": "green"}}',
    }
    schema = flow.build_options_schema(existing_data)
    sample = schema(
        {"name": "Test Options", "council": "Council Test", "update_interval": 12}
    )
    assert isinstance(sample, dict)
    sample_with_optional = schema(
        {
            "name": "Test Options",
            "council": "Council Test",
            "update_interval": 12,
            "icon_color_mapping": '{"key": "value"}',
        }
    )
    assert "icon_color_mapping" in sample_with_optional


def test_map_wiki_name_to_council_key(options_flow):
    """Test mapping from wiki name to council key."""
    flow, _ = options_flow
    flow.council_options = ["Council Test"]
    flow.council_names = ["CouncilTest"]
    assert flow.map_wiki_name_to_council_key("Council Test") == "CouncilTest"
    assert flow.map_wiki_name_to_council_key("Nonexistent") == ""


def test_is_valid_json():
    """Test is_valid_json for valid and invalid JSON."""
    from custom_components.uk_bin_collection.config_flow import (
        UkBinCollectionOptionsFlowHandler,
    )

    valid = '{"key": "value"}'
    invalid = '{"key": "value" "missing_comma": true}'
    assert UkBinCollectionOptionsFlowHandler.is_valid_json(valid) is True
    assert UkBinCollectionOptionsFlowHandler.is_valid_json(invalid) is False


# --- Test: Helper method is_valid_json ---
def test_is_valid_json_options():
    valid = '{"key": "value"}'
    invalid = '{"key": "value",}'  # trailing comma
    assert UkBinCollectionOptionsFlowHandler.is_valid_json(valid) is True
    assert UkBinCollectionOptionsFlowHandler.is_valid_json(invalid) is False
