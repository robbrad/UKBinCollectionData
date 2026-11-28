"""Offline tests for Boston's address matching and results parsing.

The council's iCM form is driven over plain HTTP (curl_cffi), since automated
Chrome is served a Cloudflare challenge on the form POST.
"""

from datetime import date

import pytest

from uk_bin_collection.uk_bin_collection.councils.BostonBoroughCouncil import (
    parse_results,
    resolve_collection_date,
    select_address,
)

OPTIONS = [
    ("", "Select address"),
    ("1", "CEDAR LODGE, FRAMPTON ROADS, FRAMPTON, BOSTON, PE20 1AY"),
    ("2", "CEDAR COTTAGE, FRAMPTON ROADS, FRAMPTON, BOSTON, PE20 1AY"),
    ("3", "7 FRAMPTON ROADS, FRAMPTON, BOSTON, PE20 1AY"),
    ("4", "17 FRAMPTON ROADS, FRAMPTON, BOSTON, PE20 1AY"),
    ("5", "7A FRAMPTON ROADS, FRAMPTON, BOSTON, PE20 1AY"),
    ("6", "THE OLD CEDAR HOUSE, FRAMPTON ROADS, FRAMPTON, BOSTON, PE20 1AY"),
]

RESULTS_PAGE = """
<div class="grid__cell grid__cell--listitem grid__cell--cols1">
 <h2 class="item__title"><a href="#">Blue Recycling Bin</a></h2>
 <div class="item__content"><div><strong>Next: </strong>Thursday 17th December</div></div>
</div>
<div class="grid__cell grid__cell--listitem grid__cell--cols1">
 <h2 class="item__title"><a href="#">Green Refuse Bin</a></h2>
 <div class="item__content"><div><strong>Next: </strong>Thursday 3rd December</div></div>
</div>
<div class="grid__cell grid__cell--listitem grid__cell--cols1">
 <h2 class="item__title"><a href="#">No date</a></h2>
</div>
"""


def test_select_address_is_start_anchored_and_whole_word():
    assert select_address(OPTIONS, "CEDAR LODGE") == "1"
    assert select_address(OPTIONS, "7") == "3"  # not 17, not 7A
    assert select_address(OPTIONS, "the old cedar house") == "6"


def test_select_address_raises_when_ambiguous():
    with pytest.raises(ValueError, match="found 2"):
        select_address(OPTIONS, "CEDAR")  # LODGE and COTTAGE; never THE OLD CEDAR


def test_select_address_raises_when_nothing_matches():
    with pytest.raises(ValueError, match="found 0"):
        select_address(OPTIONS, "99")


def test_resolve_collection_date_rolls_into_next_year():
    # Thursday 7 January 2027
    assert resolve_collection_date("Thursday 7th January", date(2026, 12, 30)) == date(
        2027, 1, 7
    )


def test_resolve_collection_date_rejects_weekday_mismatch():
    with pytest.raises(ValueError):
        resolve_collection_date("Monday 3rd December", date(2026, 11, 28))


def test_parse_results_sorts_and_skips_blocks_without_a_date():
    assert parse_results(RESULTS_PAGE, date(2026, 11, 28)) == {
        "bins": [
            {"type": "Green Refuse Bin", "collectionDate": "03/12/2026"},
            {"type": "Blue Recycling Bin", "collectionDate": "17/12/2026"},
        ]
    }


def test_parse_results_raises_on_empty_page():
    with pytest.raises(ValueError):
        parse_results("<html></html>", date(2026, 11, 28))
