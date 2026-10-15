"""Regression tests for Sevenoaks' wheelie-bin collection details layout."""

from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import TimeoutException

from uk_bin_collection.uk_bin_collection.councils.SevenoaksDistrictCouncil import (
    CouncilClass,
)

MODULE = "uk_bin_collection.uk_bin_collection.councils.SevenoaksDistrictCouncil"


def card(name, dates):
    """Build a reduced collection card with the live page's widget structure."""
    # Reduced structure of the live page: headings and dates are in separate
    # widgets, while each waste type is enclosed by a gwBorderSlim container.
    fragments = "".join(
        f'<div class="page_fragment" data-current_value="{date}">'
        f'<div><span class="value-as-text">{date}</span>'
        '<input type="hidden"></div></div>'
        for date in dates
    )
    return (
        '<div class="page_container row gwBorderSlim">'
        f'<div class="page_widget"><div data-class_name="formtable"><h2>{name}</h2></div></div>'
        '<div class="page_widget"><span class="value-as-text">Your next collection date is</span></div>'
        # The Food card also has hidden legacy fields outside the date listing.
        '<div class="page_fragment wrapper_hidden" data-current_value="Yes">'
        '<span class="value-as-text">Yes</span></div>'
        '<div class="page_widget system_widget_foundation_listing">'
        f'<div class="block_container listing">{fragments}</div></div></div>'
    )


RESULTS_HTML = (
    card("Recycling", ["Tuesday, 13 October 2026"])
    + card("Food", ["Tuesday, 13 October 2026"])
    + card("General waste", ["Tuesday, 20 October 2026"])
    + card("Garden waste", [])
    + '<div class="gwBorderSlim"><h3>Have we missed your collection?</h3></div>'
)


def test_new_layout_keeps_dates_with_their_waste_type():
    """Keep waste types paired with their dates and omit unsubscribed services."""
    assert CouncilClass()._parse_collections(RESULTS_HTML) == {
        "bins": [
            {"type": "Recycling", "collectionDate": "13/10/2026"},
            {"type": "Food", "collectionDate": "13/10/2026"},
            {"type": "General waste", "collectionDate": "20/10/2026"},
        ]
    }


def test_food_can_be_collected_with_general_waste_on_the_alternate_week():
    """Read food's own date when it coincides with the general waste week."""
    html = RESULTS_HTML.replace(
        card("Food", ["Tuesday, 13 October 2026"]),
        card("Food", ["Tuesday, 20 October 2026"]),
    )
    bins = CouncilClass()._parse_collections(html)["bins"]
    assert bins[1]["collectionDate"] == bins[2]["collectionDate"] == "20/10/2026"
    assert bins[0]["collectionDate"] == "13/10/2026"


def test_subscribed_garden_waste_and_multiple_dates():
    """Return all listed collection dates for subscribed garden waste."""
    html = card(
        "Garden waste", ["Tuesday, 20 October 2026", "Tuesday, 3 November 2026"]
    )
    assert CouncilClass()._parse_collections(html) == {
        "bins": [
            {"type": "Garden waste", "collectionDate": "20/10/2026"},
            {"type": "Garden waste", "collectionDate": "03/11/2026"},
        ]
    }


@pytest.mark.parametrize(
    "message", ["Collections suspended", "Restarting in March 2027"]
)
def test_suspended_service_is_skipped(message):
    """Ignore suspension and restart messages instead of parsing them as dates."""
    assert CouncilClass()._parse_collections(card("Garden waste", [message])) == {
        "bins": []
    }


def test_parse_data_uses_new_results_and_closes_driver():
    """Select the requested address, parse its cards and close the browser."""
    driver = MagicMock()
    driver.page_source = RESULTS_HTML
    address = MagicMock()
    address.text = "60 Hever Road, West Kingsdown, Sevenoaks, TN15 6EB"
    with patch(f"{MODULE}.create_webdriver", return_value=driver), patch(
        f"{MODULE}.Select"
    ) as select, patch.object(CouncilClass, "wait_for_element_conditions"):
        select.return_value.options = [address]
        result = CouncilClass().parse_data(
            "", postcode="TN15 6EB", paon="60 Hever Road"
        )
    select.return_value.select_by_visible_text.assert_called_once_with(address.text)
    assert result == CouncilClass()._parse_collections(RESULTS_HTML)
    driver.quit.assert_called_once()


def test_driver_is_closed_on_timeout():
    """Close the browser even when waiting for the page raises a timeout."""
    driver = MagicMock()
    with patch(f"{MODULE}.create_webdriver", return_value=driver), patch.object(
        CouncilClass, "wait_for_element_conditions", side_effect=TimeoutException
    ), pytest.raises(TimeoutException):
        CouncilClass().parse_data("", postcode="TN15 6EB", paon="60 Hever Road")
    driver.quit.assert_called_once()


@pytest.mark.parametrize("blank_date", ["", " \n\t "])
def test_blank_date_fragments_do_not_discard_valid_collections(blank_date):
    """Skip empty or whitespace dates while retaining dates in other cards."""
    html = (
        card("Recycling", [blank_date])
        + card("Food", [blank_date, "Tuesday, 13 October 2026"])
        + card("General waste", ["Tuesday, 20 October 2026"])
    )
    assert CouncilClass()._parse_collections(html) == {
        "bins": [
            {"type": "Food", "collectionDate": "13/10/2026"},
            {"type": "General waste", "collectionDate": "20/10/2026"},
        ]
    }
