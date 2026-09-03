# conftest.py

import pytest
from _pytest.config.argparsing import Parser
from _pytest.fixtures import FixtureRequest


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
