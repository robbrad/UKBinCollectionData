"""Broxbourne's own address lookup is broken; the scraper should say so."""

from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import BroxbourneCouncil

MODULE_PATH = "uk_bin_collection.uk_bin_collection.councils.BroxbourneCouncil"


def _option(text, value=""):
    opt = MagicMock()
    opt.text = text
    opt.get_attribute.return_value = value
    return opt


def _driver_returning(options):
    """A driver stub whose address <select> offers exactly these options."""
    select_element = MagicMock()
    select_element.tag_name = "select"
    select_element.get_attribute.side_effect = lambda name: {
        "multiple": None,
        "outerHTML": "<select></select>",
    }.get(name)

    driver = MagicMock()
    driver.find_element.return_value = MagicMock()
    driver.find_elements.return_value = []
    return driver, select_element, options


def _run_with(options):
    driver, select_element, opts = _driver_returning(options)
    with patch(f"{MODULE_PATH}.create_webdriver", return_value=driver), patch(
        f"{MODULE_PATH}.WebDriverWait"
    ) as wait, patch(f"{MODULE_PATH}.Select") as select_cls:
        wait.return_value.until.return_value = select_element
        select_cls.return_value.options = opts
        return BroxbourneCouncil.CouncilClass().parse_data(
            "", uprn="148048608", postcode="EN8 7FL", headless=True
        )


def test_an_empty_address_lookup_is_reported_as_the_councils_fault():
    # What the live site returns for every postcode: the placeholder plus a
    # single "My address was not found" entry, and no real addresses.
    options = [_option("Please choose..."), _option("My address was not found", "0")]
    with pytest.raises(ValueError, match="returned no addresses for postcode EN8 7FL"):
        _run_with(options)


def test_the_error_names_the_council_side_cause_not_the_uprn():
    options = [_option("Please choose..."), _option("My address was not found", "0")]
    with pytest.raises(ValueError) as excinfo:
        _run_with(options)

    message = str(excinfo.value)
    assert "its own search is currently" in message
    assert "148048608" not in message


def test_a_populated_lookup_is_not_treated_as_broken():
    options = [
        _option("Please choose..."),
        _option("1 Lampits, Hoddesdon", "148048608"),
    ]
    # Beyond the guard the flow needs the real page, so only assert that the
    # guard itself let us through rather than raising its own error.
    try:
        _run_with(options)
    except ValueError as exc:
        assert "returned no addresses" not in str(exc)
