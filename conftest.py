# conftest.py

import threading

import pytest
from _pytest.config.argparsing import Parser
from _pytest.fixtures import FixtureRequest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import frame
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True, scope="session")
def _setup_frame_helper():
    """Home Assistant's newer deprecation-reporting helper (frame.report_usage,
    used e.g. by DataUpdateCoordinator and OptionsFlowWithConfigEntry) hard-
    requires `frame.async_setup(hass)` to have been called first - normally
    done by real HA startup. Our tests use hand-rolled mock `hass` objects
    that never call it, so register one globally for the whole session.
    `loop_thread_id` must match the current thread or report_usage tries to
    schedule itself onto a (mocked, non-functional) event loop instead of
    running synchronously.
    """
    fake_hass = MagicMock(spec=HomeAssistant)
    fake_hass.loop_thread_id = threading.get_ident()
    frame.async_setup(fake_hass)


def pytest_addoption(parser: Parser) -> None:
    parser.addoption("--headless", action="store", default="True", type=str)
    parser.addoption("--local_browser", action="store", default="False", type=str)
    parser.addoption(
        "--selenium_url", action="store", default="http://localhost:4444", type=str
    )


@pytest.fixture(scope="session")
def headless_mode(request: FixtureRequest) -> str:
    return request.config.getoption("--headless")


@pytest.fixture(scope="session")
def local_browser(request: FixtureRequest) -> str:
    return request.config.getoption("--local_browser")


@pytest.fixture(scope="session")
def selenium_url(request: FixtureRequest) -> str:
    return request.config.getoption("--selenium_url")


@pytest.fixture
def hass():
    """Mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)

    # Mock the event loop with create_task as AsyncMock
    hass.loop = MagicMock()
    hass.loop.create_task = AsyncMock()

    # Mock config_entries and its flow
    hass.config_entries = MagicMock()
    hass.config_entries.flow = MagicMock()

    # Mock asynchronous methods with AsyncMock
    hass.config_entries.flow.async_init = AsyncMock()
    hass.config_entries.flow.async_configure = AsyncMock()

    # Mock async_get_entry to return a MockConfigEntry when called
    hass.config_entries.async_get_entry = AsyncMock()

    # Mock async_unload as an AsyncMock
    hass.config_entries.async_unload = AsyncMock(return_value=True)

    # Mock async_block_till_done as an AsyncMock
    hass.async_block_till_done = AsyncMock()
    hass.async_add_executor_job = AsyncMock()  # Ensure compatibility with async calls

    return hass


@pytest.fixture
def enable_custom_integrations():
    """Fixture to enable custom integrations."""
    with patch("homeassistant.helpers.discovery.load_platform") as mock_load:
        yield mock_load
