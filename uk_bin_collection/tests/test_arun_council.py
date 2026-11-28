"""Unit tests for Arun's address-dropdown matching."""

import pytest

from uk_bin_collection.uk_bin_collection.councils.ArunCouncil import CouncilClass

OPTIONS = [
    "Please select your property",
    "1 MERRYFIELD CRESCENT, ANGMERING",
    "1A MERRYFIELD CRESCENT, ANGMERING",
    "10 MERRYFIELD CRESCENT, ANGMERING",
    "11 MERRYFIELD CRESCENT, ANGMERING",
    "FLAT 1, 12 MERRYFIELD CRESCENT, ANGMERING",
]


def test_whole_number_matches_only_itself_not_longer_numbers():
    assert (
        CouncilClass._pick_address_option(OPTIONS, "1")
        == "1 MERRYFIELD CRESCENT, ANGMERING"
    )


def test_number_with_letter_suffix_matches():
    assert (
        CouncilClass._pick_address_option(OPTIONS, "1A")
        == "1A MERRYFIELD CRESCENT, ANGMERING"
    )


def test_number_is_not_matched_mid_string():
    with pytest.raises(ValueError):
        CouncilClass._pick_address_option(OPTIONS, "12")


def test_no_match_raises_and_lists_options():
    with pytest.raises(ValueError, match="found 0"):
        CouncilClass._pick_address_option(OPTIONS, "99")


def test_more_than_one_match_raises():
    options = ["1 HIGH STREET, A", "1 LOW STREET, A"]
    with pytest.raises(ValueError, match="found 2"):
        CouncilClass._pick_address_option(options, "1")
