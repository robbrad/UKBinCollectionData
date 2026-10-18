"""Unit tests for Gedling's Liberty Create bin collections portal."""

import json
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlparse

import pytest

from uk_bin_collection.uk_bin_collection.councils.GedlingBoroughCouncil import (
    CouncilClass,
)

MODULE_PATH = "uk_bin_collection.uk_bin_collection.councils.GedlingBoroughCouncil"

# The pages, trimmed from the live portal
PAGE_HTML = (
    '<script>var mats = {"csrf":"ab12"}; '
    "var AJAX_DYNAMIC_URL = '/w/webpage/bin-collections?webpage_token=t1';</script>"
)
COLLECTIONS_PAGE_HTML = '<script>var mats = {"csrf":"cd34"};</script>'
FORM_HTML = """<form>
<input type="hidden" name="form_check" value="old">
<input type="hidden" name="submitted_page_id" value="PAG0000634GBSHB1">
<input type="hidden" name="submission_token" value="st1">
<input type="hidden" name="payload[P][W][PCL0004494GBSHB1][formtable][C_1][PCF0016553GBSHB1]" value="0">
<input type="text" name="payload[P][W][PCL0004494GBSHB1][formtable][C_1][PCF0014909GBSHB1]" value="">
<input type="submit" name="payload[P][W][PCL0004556GBSHB1][formtable][C_2][PCF0015021GBSHB1]" value="View collection days">
</form>"""
ADDRESSES = [
    {"id": "53123", "summary_address": "11 Gedling Road Arnold Nottingham NG5 6NQ"},
    {"id": "53124", "summary_address": "11A Gedling Road Arnold Nottingham NG5 6NQ"},
    {"id": "24433", "summary_address": "Rose Cottage Gedling Road Arnold Nottingham NG5 6NQ"},
]
COLLECTIONS_HTML = """<table>
<tr><th>Service</th><th>Day</th><th>Date</th></tr>
<tr><td><div data-current_value="Glass Collection Service"></div></td><td>Tuesday</td><td>Tue, 27 Oct 2026</td></tr>
<tr><td><div data-current_value="General Collection Service"></div></td><td>Tuesday</td><td>Tue, 20 Oct 2026</td></tr>
<tr><td><div data-current_value="Recycling Collection Service"></div></td><td>Tuesday</td><td>No collection</td></tr>
</table>"""


class FakePortal:
    """Answers the portal's requests the way the live site does, and keeps
    the address form that was submitted."""

    def __init__(self, addresses=ADDRESSES, page_html=PAGE_HTML):
        self.addresses = addresses
        self.page_html = page_html
        self.headers = {}
        self.submitted = None

    def get(self, url, timeout=None):
        path = urlparse(url).path
        text = self.page_html if path == "/w/webpage/bin-collections" else COLLECTIONS_PAGE_HTML
        return SimpleNamespace(text=text, raise_for_status=lambda: None)

    def post(self, url, headers=None, data=None, timeout=None):
        if data.get("code_action") == "search":
            body = {"result": "success", "response": {"options": self.addresses}}
        elif "submit_fragment_id" in data:
            self.submitted = data
            body = {"status": "redirect", "redirect_url": "/w/webpage/bin-collections-4-weeks?id=9"}
        elif "4-weeks" in url:
            body = {"data": COLLECTIONS_HTML}
        else:
            body = {"data": FORM_HTML}
        return SimpleNamespace(json=lambda: body, raise_for_status=lambda: None)


def run(portal, house, postcode="NG5 6NQ"):
    with patch(f"{MODULE_PATH}.requests.Session", return_value=portal):
        return CouncilClass().parse_data("", postcode=postcode, paon=house)


def test_parse_data_returns_the_addresses_collections_in_date_order():
    assert run(FakePortal(), "11") == {
        "bins": [
            {"type": "General", "collectionDate": "20/10/2026"},
            {"type": "Glass", "collectionDate": "27/10/2026"},
        ]
    }


@pytest.mark.parametrize(
    "house, address_id",
    [
        ("11", "53123"),  # not 11A
        ("11a", "53124"),
        ("11 Gedling Road", "53123"),
        ("Rose Cottage", "24433"),
    ],
)
def test_the_address_is_chosen_by_its_start(house, address_id):
    portal = FakePortal()
    run(portal, house)
    field = "payload[P][W][PCL0004494GBSHB1][formtable][C_1][PCF0016554GBSHB1]"
    assert portal.submitted[field] == address_id


def test_the_submit_leaves_out_the_type_ahead_box():
    # Sending it, even empty, makes the portal answer with an empty page
    portal = FakePortal()
    run(portal, "11")
    assert not any("PCF0014909GBSHB1" in name for name in portal.submitted)
    assert portal.submitted["form_check"] == "ab12"
    assert portal.submitted["submit_fragment_id"] == "PCF0015021GBSHB1"


def test_an_address_not_at_the_postcode_is_an_error_not_a_guess():
    with pytest.raises(ValueError, match="could not find '12'.*11 Gedling Road"):
        run(FakePortal(), "12")


def test_a_postcode_without_addresses_is_an_error():
    with pytest.raises(ValueError, match="no addresses for postcode NG5 6NQ"):
        run(FakePortal(addresses=[]), "11")


def test_the_postcode_and_house_are_both_needed():
    with pytest.raises(ValueError, match="postcode and a house number or name"):
        CouncilClass().parse_data("", postcode="NG5 6NQ")


def test_a_page_without_its_action_url_is_reported_as_changed():
    # Not a search of a malformed URL, which would look like "no addresses"
    page_html = PAGE_HTML.split("var AJAX_DYNAMIC_URL")[0] + "</script>"
    with pytest.raises(ValueError, match="no action URL"):
        run(FakePortal(page_html=page_html), "11")
