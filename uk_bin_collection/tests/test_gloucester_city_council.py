"""Gloucester must wait for the address option, not just the dropdown element."""

from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import TimeoutException

from uk_bin_collection.uk_bin_collection.councils import GloucesterCityCouncil

MODULE_PATH = "uk_bin_collection.uk_bin_collection.councils.GloucesterCityCouncil"
UPRN = "100120479507"
POSTCODE = "GL2 0RR"


def _option(value):
    opt = MagicMock()
    opt.get_attribute.return_value = value
    return opt


class _FakeWait:
    """Stands in for WebDriverWait, running conditions against a fake driver.

    `EC.*` conditions are patched out to return sentinels, so the only
    condition that actually executes here is the scraper's own callable - which
    is the behaviour under test.
    """

    def __init__(self, driver, *args, **kwargs):
        self._driver = driver

    def until(self, condition, *args, **kwargs):
        if callable(condition) and not isinstance(condition, MagicMock):
            deadline = 50
            while deadline:
                result = condition(self._driver)
                if result:
                    return result
                deadline -= 1
            raise TimeoutException()
        return MagicMock()


def _driver_with(option_values, populate_after=0):
    """A driver whose chooseAddress select gains its options after N polls."""
    state = {"polls": 0}
    select_element = MagicMock()

    def find_element(by, name):
        if name == "chooseAddress":
            state["polls"] += 1
            return select_element
        return MagicMock()

    driver = MagicMock()
    driver.find_element.side_effect = find_element

    def options_now():
        if state["polls"] <= populate_after:
            return [_option("")]
        return [_option("")] + [_option(v) for v in option_values]

    return driver, options_now, state


def _run(option_values, populate_after=0):
    driver, options_now, state = _driver_with(option_values, populate_after)

    select_instance = MagicMock()
    type(select_instance).options = property(lambda self: options_now())

    with patch(f"{MODULE_PATH}.create_webdriver", return_value=driver), patch(
        f"{MODULE_PATH}.WebDriverWait", _FakeWait
    ), patch(f"{MODULE_PATH}.Select", return_value=select_instance), patch(
        f"{MODULE_PATH}.EC"
    ), patch(
        f"{MODULE_PATH}.check_postcode", return_value=True
    ), patch(
        f"{MODULE_PATH}.check_uprn", return_value=True
    ), patch(
        f"{MODULE_PATH}.time.sleep"
    ):
        try:
            GloucesterCityCouncil.CouncilClass().parse_data(
                "", uprn=UPRN, postcode=POSTCODE, headless=True
            )
        except ValueError:
            # The scraper's own "UPRN not offered" error is under test.
            raise
        except Exception:
            # Anything past the address selection runs into the mocked page
            # source. Everything this module asserts on has already happened.
            pass
    return select_instance, state


def test_it_waits_for_the_option_to_appear_before_selecting():
    # The dropdown exists from the first poll but is empty until the third;
    # the scraper must keep polling rather than selecting into an empty list.
    select_instance, state = _run([UPRN], populate_after=2)

    select_instance.select_by_value.assert_called_once_with(UPRN)
    assert state["polls"] > 2, "should have polled until the options arrived"


def test_it_selects_immediately_when_the_options_are_already_there():
    select_instance, _ = _run([UPRN], populate_after=0)
    select_instance.select_by_value.assert_called_once_with(UPRN)


def test_a_uprn_that_is_never_offered_is_a_clear_error():
    with pytest.raises(ValueError, match="was not offered for postcode"):
        _run(["100000000001", "100000000002"], populate_after=0)


def test_the_error_names_the_uprn_and_the_count_of_addresses_offered():
    with pytest.raises(ValueError) as excinfo:
        _run(["100000000001", "100000000002"], populate_after=0)

    message = str(excinfo.value)
    assert UPRN in message
    assert POSTCODE in message
    assert "2 address" in message
