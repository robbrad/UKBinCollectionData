"""Unit tests for Midlothian's address-dropdown matching."""

import pytest

from uk_bin_collection.uk_bin_collection.councils.MidlothianCouncil import (
    CouncilClass,
)

OPTIONS = [
    "Select an address",
    "5 Example Road, Dalkeith",
    "52 Example Road, Dalkeith",
    "52A Example Road, Dalkeith",
    "152 Example Road, Dalkeith",
    "Flat 5, 9 Example Road, Dalkeith",
]


def test_whole_number_matches_only_itself():
    assert CouncilClass.pick_address_text(OPTIONS, "52") == "52 Example Road, Dalkeith"


def test_single_digit_does_not_match_longer_numbers():
    assert CouncilClass.pick_address_text(OPTIONS, "5") == "5 Example Road, Dalkeith"


def test_suffix_letter_is_its_own_address():
    assert (
        CouncilClass.pick_address_text(OPTIONS, "52A") == "52A Example Road, Dalkeith"
    )


def test_number_is_not_matched_mid_string():
    with pytest.raises(ValueError, match="found 0"):
        CouncilClass.pick_address_text(OPTIONS, "9")


def test_ambiguous_number_raises_with_candidates():
    options = ["3 High Street, A", "3 Low Street, A"]
    with pytest.raises(ValueError, match="found 2"):
        CouncilClass.pick_address_text(options, "3")
