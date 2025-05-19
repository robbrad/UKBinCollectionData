# custom_components/uk_bin_collection/tests/common_utils.py

import uuid
from unittest.mock import Mock, AsyncMock  # Import AsyncMock
from homeassistant import config_entries
import asyncio


class MockConfigEntry:
    """Mock for Home Assistant ConfigEntry."""

    def __init__(
        self,
        domain,
        data=None,
        options=None,
        title=None,
        unique_id=None,
        source=config_entries.SOURCE_USER,
        entry_id=None,
        version=1,
    ):
        """Initialize a mock config entry."""
        self.domain = domain
        self.data = data or {}
        self.options = options or {}
        self.title = title or "Mock Title"
        self.unique_id = unique_id
        self.source = source
        self.entry_id = entry_id or uuid.uuid4().hex
        self.version = version
        self.state = config_entries.ConfigEntryState.NOT_LOADED

    def add_to_hass(self, hass):
        """Add the mock config entry to Home Assistant."""
        # Mock the async_add method to accept the entry
        hass.config_entries.async_add.return_value = None
        hass.config_entries.async_add(self)

        # Mock async_setup to be an AsyncMock that returns True
        hass.config_entries.async_setup = AsyncMock(return_value=True)

        # Mock the create_task to immediately run the coroutine
        # Define a coroutine that runs async_setup and updates the entry state
        async def run_setup(entry_id):
            result = await hass.config_entries.async_setup(entry_id)
            if result:
                self.state = config_entries.ConfigEntryState.LOADED
            else:
                self.state = config_entries.ConfigEntryState.SETUP_ERROR

        # Assign the coroutine as a side effect to create_task
        hass.loop.create_task = AsyncMock(
            side_effect=lambda coro: asyncio.create_task(run_setup(self.entry_id))
        )
