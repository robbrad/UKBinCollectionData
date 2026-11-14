"""East Suffolk renames its bins every so often; the cleaner must cope with each wording."""

import pytest

from uk_bin_collection.uk_bin_collection.councils.EastSuffolkCouncil import (
    clean_bin_type,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Food Waste (Green Bin)", "Food Waste"),
        ("Refuse (Black Bin) ", "Refuse"),
        ("Garden (brown) Waste", "Garden Waste"),
        ("Recycling - Standard Bin", "Recycling"),
        ("Recycling - standard bin (Blue)", "Recycling"),
        ("\U0001f5d1️ Refuse (Black)", "Refuse"),
        ("plain waste", "Plain Waste"),
    ],
    ids=[
        "trailing-bracket",
        "trailing-space",
        "mid-name-bracket",
        "old-standard-bin-wording",
        "both-wordings",
        "emoji-prefix",
        "no-descriptor",
    ],
)
def test_bin_names_are_cleaned_for_every_wording(raw, expected):
    assert clean_bin_type(raw) == expected
