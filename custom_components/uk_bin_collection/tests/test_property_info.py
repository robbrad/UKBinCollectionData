"""Test UK Bin Collection property info module."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

# Import the functions from your component using relative imports
from ..property_info import API_KEY, async_get_property_info


# You can create mock responses for your tests
@pytest.fixture
def mock_property_response():
    """Return a mock property response."""
    return {
        "street_name": "Test Street",
        "admin_ward": "Test Ward",
        "postcode": "TE1 1ST",
        "LAD24CD": "E12345678",
        "postal_town": "Test Town",
    }


@pytest.mark.asyncio
async def test_async_get_property_info_success(mock_property_response):
    """Test successful property info retrieval."""

    # Create a class to properly mock aiohttp responses with logging
    class MockResponse:
        def __init__(self, json_data, status):
            self.json_data = json_data
            self.status = status

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def json(self):
            return self.json_data

    # Define response data
    google_data = {
        "results": [
            {
                "address_components": [
                    {"types": ["postal_code"], "long_name": "TE1 1ST"},
                    {"types": ["route"], "long_name": "Test Street"},
                    {"types": ["postal_town"], "long_name": "Test Town"},
                ]
            }
        ],
        "status": "OK",
    }

    postcodes_data = {
        "status": 200,
        "result": {"admin_ward": "Test Ward", "codes": {"admin_district": "E12345678"}},
    }

    # Create mock session class that properly implements context manager
    class MockClientSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        # Make get a regular method that returns a response object, not a coroutine
        def get(self, url, **kwargs):
            if "maps.googleapis.com" in url:
                return MockResponse(google_data, 200)
            else:  # postcodes.io
                return MockResponse(postcodes_data, 200)

    # Apply patch to aiohttp.ClientSession to return our mock
    with patch("aiohttp.ClientSession", return_value=MockClientSession()):
        # Call the function
        result = await async_get_property_info(51.5074, -0.1278)

        # Assert expected result
        assert result == mock_property_response


@pytest.mark.asyncio
async def test_async_get_property_info_google_error():
    """Test handling of Google API errors."""
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.__aenter__.return_value = mock_response

        mock_session.return_value.get = AsyncMock(return_value=mock_response)

        with patch("logging.Logger.warning") as mock_warning, patch(
            "logging.Logger.error"
        ) as mock_error:

            # Call the function
            result = await async_get_property_info(51.5074, -0.1278)

            # Check if any warnings or errors were logged
            if mock_warning.called:
                print(f"Warning logged: {mock_warning.call_args}")
            if mock_error.called:
                print(f"Error logged: {mock_error.call_args}")

        # Assert expected result for error condition
        assert result is None
