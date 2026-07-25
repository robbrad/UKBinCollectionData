"""Unit tests for the Broxtowe Borough Council role-based field lookup."""

from unittest.mock import MagicMock

import pytest

from uk_bin_collection.uk_bin_collection.councils.BroxtoweBoroughCouncil import (
    CouncilClass,
)


def fake_element(element_id: str) -> MagicMock:
    element = MagicMock()
    element.get_attribute.side_effect = lambda name: (
        element_id if name == "id" else None
    )
    return element


def fake_driver(elements) -> MagicMock:
    driver = MagicMock()
    driver.find_elements.return_value = elements
    return driver


def test_find_field_by_role_matches_regardless_of_the_numeric_id():
    # The council can republish the form with a different numeric id at any
    # time; only the role suffix (TB/BTN/DDL/FormGroup) should matter.
    driver = fake_driver([fake_element("ctl00_ContentPlaceHolder1_FF9999TB")])

    element = CouncilClass()._find_field_by_role(driver, "TB", tag="input")

    assert element.get_attribute("id") == "ctl00_ContentPlaceHolder1_FF9999TB"


def test_find_field_by_role_raises_when_no_match():
    driver = fake_driver([])

    with pytest.raises(ValueError, match="found 0"):
        CouncilClass()._find_field_by_role(driver, "TB", tag="input", timeout=0)


def test_find_field_by_role_raises_when_ambiguous():
    driver = fake_driver(
        [
            fake_element("ctl00_ContentPlaceHolder1_FF1111TB"),
            fake_element("ctl00_ContentPlaceHolder1_FF2222TB"),
        ]
    )

    with pytest.raises(ValueError, match="found 2"):
        CouncilClass()._find_field_by_role(driver, "TB", tag="input", timeout=0)
