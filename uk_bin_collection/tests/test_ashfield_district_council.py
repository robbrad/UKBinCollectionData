"""Unit tests for Ashfield's address matching and collection parsing.

The council replaced its Liberty Create portal with its own JSON endpoints
(/api/address/search/<postcode> and /api/address/collections/<uprn>).
Fixtures are cut down from the live responses.
"""

import pytest

from uk_bin_collection.uk_bin_collection.councils.AshfieldDistrictCouncil import (
    parse_collections,
    select_uprn,
)


def _address(text: str, uprn: str) -> dict:
    return {"DPA": {"ADDRESS": text, "UPRN": uprn}}


RESULTS = [
    _address("1, PENROSE COURT, SELSTON, NOTTINGHAM, NG16 6RH", "100"),
    _address("10, PENROSE COURT, SELSTON, NOTTINGHAM, NG16 6RH", "110"),
    _address("1A, PENROSE COURT, SELSTON, NOTTINGHAM, NG16 6RH", "101"),
    _address("11, PENROSE COURT, SELSTON, NOTTINGHAM, NG16 6RH", "111"),
    _address("FLAT 2, THE OLD MILL, SELSTON, NOTTINGHAM, NG16 6RH", "200"),
]


def test_house_number_matches_only_the_whole_number():
    assert select_uprn(RESULTS, "1") == "100"
    assert select_uprn(RESULTS, "10") == "110"
    assert select_uprn(RESULTS, "1A") == "101"


def test_house_name_match_is_case_insensitive():
    assert select_uprn(RESULTS, "flat 2") == "200"


def test_number_in_the_middle_of_an_address_does_not_match():
    with pytest.raises(ValueError, match="found 0"):
        select_uprn(RESULTS, "2")


def test_ambiguous_match_raises_and_lists_candidates():
    duplicated = RESULTS + [
        _address("1, PENROSE COURT, SELSTON, NOTTINGHAM, NG16 6RH", "999")
    ]
    with pytest.raises(ValueError, match="found 2") as error:
        select_uprn(duplicated, "1")
    assert "PENROSE COURT" in str(error.value)


def test_parse_collections_converts_dates():
    parsed = parse_collections(
        [
            {
                "service": "Domestic Recycling Collection Service",
                "date": "03/12/2026 00:00:00",
            },
            {
                "service": "Residual Waste Collection Service",
                "date": "10/12/2026 00:00:00",
            },
        ]
    )
    assert parsed == {
        "bins": [
            {
                "type": "Domestic Recycling Collection Service",
                "collectionDate": "03/12/2026",
            },
            {
                "type": "Residual Waste Collection Service",
                "collectionDate": "10/12/2026",
            },
        ]
    }


def test_no_collections_raises_instead_of_returning_empty():
    with pytest.raises(ValueError, match="no collection dates"):
        parse_collections([])
