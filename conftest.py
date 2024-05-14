import pytest

def pytest_addoption(parser):
    parser.addoption("--headless", action="store", default="True")

@pytest.fixture(scope='session')
def headless_mode(request):
    headless_mode_value = request.config.option.headless
    if headless_mode_value is None:
        pytest.skip()
    return headless_mode_value