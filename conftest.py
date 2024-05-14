import os

def pytest_generate_tests(metafunc):
    if 'HEADLESS' not in os.environ:
        os.environ['HEADLESS'] = "False"