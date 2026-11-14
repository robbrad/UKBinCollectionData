"""Newcastle's ReCollect address search is a fuzzy prefix match, so the scraper must pick carefully.

Picking the wrong parcel returns another household's collection days without any error,
which is the failure these tests are here to prevent.
"""

import pytest

from uk_bin_collection.uk_bin_collection.councils.NewcastleCityCouncil import (
    _pick,
    _starts_with_paon,
)


def parcel(name, place_id):
    return {"type": "parcel", "place_id": place_id, "name": name}


PARCELS = [
    parcel("1 Example Street, Newcastle upon Tyne, NE1 1AA", "no-1-example"),
    parcel("10 Example Street, Newcastle upon Tyne, NE1 1AA", "no-10-example"),
    parcel("Flat 1, 12 Example Street, Newcastle upon Tyne, NE1 1AA", "flat-1-no-12"),
    parcel("1 Other Road, Newcastle upon Tyne, NE2 2BB", "no-1-other"),
]


@pytest.mark.parametrize(
    "label, paon, expected",
    [
        ("1 Example Street, NE1 1AA", "1", True),
        ("10 Example Street, NE1 1AA", "1", False),
        ("11 Example Street, NE1 1AA", "1", False),
        ("1A Example Street, NE1 1AA", "1", False),
        ("1a Example Street, NE1 1AA", "1A", True),
        ("Flat 1, 12 Example Street, NE1 1AA", "1", False),
        ("1 Example Street, NE1 1AA", "1 example street", True),
        ("1  EXAMPLE STREET, NE1 1AA", "1, Example Street", True),
    ],
)
def test_prefix_match_is_whole_word(label, paon, expected):
    assert _starts_with_paon(label, paon) is expected


def test_the_house_number_picks_that_house_not_a_flat_or_a_longer_number():
    assert _pick(PARCELS, "1", "NE1 1AA") == "no-1-example"
    assert _pick(PARCELS, "10", "NE1 1AA") == "no-10-example"


def test_the_postcode_keeps_the_same_number_on_another_street_apart():
    assert _pick(PARCELS, "1", "NE2 2BB") == "no-1-other"


def test_an_unknown_house_number_is_refused_not_replaced_by_another_address():
    assert _pick(PARCELS, "7", "NE1 1AA") is None


def test_a_number_that_only_exists_in_a_different_postcode_is_refused():
    assert _pick(PARCELS, "10", "NE2 2BB") is None
    assert _pick(PARCELS, "1", "NE9 9ZZ") is None
