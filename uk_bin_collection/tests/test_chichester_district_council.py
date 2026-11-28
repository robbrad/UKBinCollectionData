"""Unit tests for Chichester's address matching and results parsing.

The council's iCM form is driven over plain HTTP (curl_cffi), since automated
Chrome is served a Cloudflare Turnstile challenge. Fixtures are cut down from
the live responses.
"""

import pytest

from uk_bin_collection.uk_bin_collection.councils.ChichesterDistrictCouncil import (
    address_text,
    parse_results,
    select_address,
)


def _address(line1, line3: str, uprn: int, line2=None) -> dict:
    return {
        "udprn": uprn,
        "uprn": uprn,
        "company": None,
        "line1": line1,
        "line2": line2,
        "line3": line3,
        "line4": "Kirdford",
        "town": "Billingshurst",
        "postcode": "RH14 0JT",
    }


ADDRESSES = [
    _address(7, "Plaistow Road", 1),
    _address(17, "Plaistow Road", 2),
    _address("7A", "Plaistow Road", 3),
    _address("Flat 2", "Old Mill", 4),
]

RESULTS_PAGE = """
<div class="gi-summary-blocklist__row"><div class="gi-summary-blocklist__key">Recycling</div>
<div class="gi-summary-blocklist__value"> Thursday 10
 December 2026 </div></div>
<div class="gi-summary-blocklist__row"><div class="gi-summary-blocklist__key">Food waste</div>
<div class="gi-summary-blocklist__value">Monday 30 November 2026</div></div>
<div class="gi-summary-blocklist__row"><div class="gi-summary-blocklist__key">No value row</div></div>
"""


def test_address_text_skips_empty_lines_and_keeps_numbers():
    assert address_text(ADDRESSES[0]) == (
        "7, Plaistow Road, Kirdford, Billingshurst, RH14 0JT"
    )


def test_number_matches_only_the_whole_number():
    assert select_address(ADDRESSES, "7")["uprn"] == 1
    assert select_address(ADDRESSES, "17")["uprn"] == 2
    assert select_address(ADDRESSES, "7A")["uprn"] == 3


def test_house_name_match_is_case_insensitive():
    assert select_address(ADDRESSES, "flat 2")["uprn"] == 4


def test_no_substring_fallback():
    with pytest.raises(ValueError, match="found 0"):
        select_address(ADDRESSES, "Plaistow")


def test_ambiguous_match_raises_and_lists_candidates():
    duplicated = ADDRESSES + [_address(7, "Other Road", 9)]
    with pytest.raises(ValueError, match="found 2") as error:
        select_address(duplicated, "7")
    assert "Other Road" in str(error.value)


def test_results_are_parsed_and_sorted_by_date():
    assert parse_results(RESULTS_PAGE)["bins"] == [
        {"collectionDate": "30/11/2026", "type": "Food waste"},
        {"collectionDate": "10/12/2026", "type": "Recycling"},
    ]


def test_page_without_dates_raises_instead_of_returning_empty():
    with pytest.raises(ValueError, match="collection dates"):
        parse_results("<html><title>Just a moment...</title></html>")
