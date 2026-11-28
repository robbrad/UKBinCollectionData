"""Offline tests for Stockton-on-Tees' address matching and results parsing.

The council's iCM form is driven over plain HTTP (curl_cffi), since automated
Chrome is served a Cloudflare challenge on the form POST.
"""

from datetime import date

import pytest

from uk_bin_collection.uk_bin_collection.councils.StocktonOnTeesCouncil import (
    parse_results,
    select_address,
)

TODAY = date(2026, 11, 28)


def _address(line1: str) -> dict:
    return {"line1": line1, "line2": "", "town": "STOCKTON-ON-TEES", "udprn": 1}


ADDRESSES = [
    _address("1 BISHOPTON AVENUE"),
    _address("11 BISHOPTON AVENUE"),
    _address("1A BISHOPTON AVENUE"),
]


def _page(garden_html: str) -> str:
    return f"""
<div class="myaccount-block__item--waste"><p class="myaccount-block__date myaccount-block__date--bin myaccount-block__date--waste"> Thu 10 December 2026</p></div>
<div class="myaccount-block__item--recycling"><p class="myaccount-block__date myaccount-block__date--bin myaccount-block__date--recycling"> Today</p></div>
<div class="myaccount-block__item myaccount-block__item--bin myaccount-block__item--garden">{garden_html}</div>
"""


def test_select_address_is_start_anchored_and_whole_word():
    assert select_address(ADDRESSES, "1") is ADDRESSES[0]
    assert select_address(ADDRESSES, "11") is ADDRESSES[1]


def test_select_address_raises_on_zero_or_multiple():
    with pytest.raises(ValueError, match="found 0"):
        select_address(ADDRESSES, "3")
    with pytest.raises(ValueError, match="found 2"):
        select_address([ADDRESSES[0], _address("1 OTHER ROAD")], "1")


def test_parse_results_ignores_the_last_garden_collection_when_service_ended():
    garden = "<p>The Garden Waste service has now ended. Your last collection was: <strong> Thu 12 November 2026</strong>.</p>"
    assert parse_results(_page(garden), TODAY) == {
        "bins": [
            {"type": "Recycling bin", "collectionDate": "28/11/2026"},
            {"type": "Rubbish bin", "collectionDate": "10/12/2026"},
        ]
    }


def test_parse_results_includes_upcoming_garden_date():
    garden = "<p>Next collection <strong>Fri 04 December 2026</strong></p>"
    types = [b["type"] for b in parse_results(_page(garden), TODAY)["bins"]]
    assert types == ["Recycling bin", "Garden waste bin", "Rubbish bin"]


def test_parse_results_skips_garden_when_date_not_available():
    garden = "<strong>Date not available</strong>"
    assert len(parse_results(_page(garden), TODAY)["bins"]) == 2


def test_parse_results_raises_when_main_dates_missing():
    with pytest.raises(ValueError, match="waste"):
        parse_results("<html></html>", TODAY)
