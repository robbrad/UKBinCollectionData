import pytest
from _pytest.config.argparsing import Parser
from _pytest.fixtures import FixtureRequest
import asyncio

from pytest_socket import enable_socket, disable_socket, socket_allow_hosts

@pytest.hookimpl(trylast=True)
def pytest_runtest_setup():
    enable_socket()
    socket_allow_hosts(None)  # Allow all hosts

## Integration Tests
def pytest_addoption(parser: Parser) -> None:
    parser.addoption("--headless", action="store", default="True", type=str)
    parser.addoption("--local_browser", action="store", default="False", type=str)
    parser.addoption("--selenium_url", action="store", default="http://localhost:4444", type=str)

@pytest.fixture(scope='session')
def headless_mode(request: FixtureRequest) -> str:
    headless_mode_value = str(request.config.getoption("--headless"))
    return headless_mode_value

@pytest.fixture(scope='session')
def local_browser(request: FixtureRequest) -> str:
    local_browser_value = str(request.config.getoption("--local_browser"))
    return local_browser_value

@pytest.fixture(scope='session')
def selenium_url(request: FixtureRequest) -> str:
    selenium_url_value = str(request.config.getoption("--selenium_url"))
    return selenium_url_value