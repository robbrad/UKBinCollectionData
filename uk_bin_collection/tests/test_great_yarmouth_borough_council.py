"""Unit tests for Great Yarmouth's address and results parsing.

The council's iCM form is posted over plain HTTP (curl_cffi), since the final
submission gets a Cloudflare Turnstile challenge in automated Chrome. The
results page gives dates with no year ("Tuesday  1 December"), so the year has
to be inferred. Fixtures are cut down from the live page.
"""

from datetime import date

import pytest

from uk_bin_collection.uk_bin_collection.councils.GreatYarmouthBoroughCouncil import (
    address_for_uprn,
    parse_collection_date,
    parse_collections,
)

RESULTS_PAGE = """
<div class="collection-area"><div class="collection-image-area"><img alt="green bin" src="x"/></div>
<div class="collection-detail"><b>Tuesday  1 December</b><br/>Recycling bins (green) will be emptied</div></div>
<div class="collection-area"><div class="collection-image-area"><img alt="black bin" src="x"/></div>
<div class="collection-detail"><b>Monday 4 January</b><br/>General Waste bins (black) will be emptied</div></div>
<div class="collection-area"><div class="collection-image-area"><img alt="black bin" src="x"/></div>
<div class="collection-detail"><b>Tuesday 15 December</b><br/>General Waste bins (black) will be emptied</div></div>
"""


def test_december_date_keeps_this_year():
    assert parse_collection_date("Tuesday  1 December", date(2026, 11, 28)) == date(
        2026, 12, 1
    )


def test_january_date_seen_in_december_rolls_into_next_year():
    assert parse_collection_date("Monday 4 January", date(2026, 12, 20)) == date(
        2027, 1, 4
    )


def test_weekday_that_disagrees_with_the_date_raises():
    with pytest.raises(ValueError):
        parse_collection_date("Friday 1 December", date(2026, 11, 28))


def test_collections_keep_the_earliest_date_per_bin_type():
    bins = parse_collections(RESULTS_PAGE, date(2026, 11, 28))["bins"]
    assert sorted(bins, key=lambda b: b["type"]) == [
        {"type": "General Waste", "collectionDate": "15/12/2026"},
        {"type": "Recycling", "collectionDate": "01/12/2026"},
    ]


def test_year_rollover_is_applied_to_parsed_collections():
    html = """<div class="collection-area"><img alt="brown bin" src="x"/>
    <div class="collection-detail"><b>Monday 4 January</b><br/>Garden Waste</div></div>"""
    assert parse_collections(html, date(2026, 12, 20))["bins"] == [
        {"type": "Garden Waste", "collectionDate": "04/01/2027"}
    ]


def test_page_without_collections_raises_instead_of_returning_empty():
    with pytest.raises(ValueError, match="collection dates"):
        parse_collections("<html><title>Just a moment...</title></html>", date.today())


ADDRESSES = [
    {"uprn": "100090834754", "property": "171"},
    {"uprn": "100090834792", "property": "228"},
]


def test_address_is_found_by_exact_uprn():
    assert address_for_uprn(ADDRESSES, "100090834792")["property"] == "228"


def test_unknown_uprn_raises():
    with pytest.raises(ValueError, match="found 0"):
        address_for_uprn(ADDRESSES, "1009083479")
