"""Unit tests for the Tower Hamlets AchieveForms scraper.

The council's form now lists upcoming collections in a table filled by a
server-side lookup, rather than in the single-value fields the old
Selenium scraper read. These tests stand in for the form's lookups with
rows modelled on its live responses, so no network or browser is needed.
"""

from datetime import date, datetime
from unittest.mock import patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import TowerHamletsCouncil
from uk_bin_collection.uk_bin_collection.councils.TowerHamletsCouncil import (
    ADDRESS_LOOKUP,
    DATES_LOOKUP,
    TIMEBAND_LOOKUP,
    CouncilClass,
    with_year,
)

ADDRESSES = [
    {"display": "10, Hanbury Street, E1 6QR", "name": "6001104"},
    {"display": "12, Hanbury Street, E1 6QR", "name": "6001105"},
]
DATES = [
    {
        "CollectionService": "Recycling",
        "CollectionDay": "Monday",
        "CollectionDate": "05 October",
    },
    {
        "CollectionService": "General Waste",
        "CollectionDay": "Wednesday",
        "CollectionDate": "07 October",
    },
]
TIMEBANDS = [
    {"single_AM_Timeband": "7:40am to 9:40am", "single_PM_Timeband": "6:40pm to 8:40pm"}
]


class FakeForm:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def lookup(self, lookup_id, fields):
        self.calls.append((lookup_id, fields))
        return self.responses.get(lookup_id, [])


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 2, 9, 0)


def run(responses, **kwargs):
    form = FakeForm(responses)
    with patch.object(
        TowerHamletsCouncil, "AchieveFormsSession", return_value=form
    ), patch.object(TowerHamletsCouncil, "datetime", FixedDatetime):
        return CouncilClass().parse_data("", **kwargs), form


def test_reads_the_collection_table_by_uprn():
    data, form = run({DATES_LOOKUP: DATES}, uprn="6001104")
    assert data["bins"] == [
        {"type": "Recycling", "collectionDate": "05/10/2026"},
        {"type": "General Waste", "collectionDate": "07/10/2026"},
    ]
    assert form.calls[0] == (
        DATES_LOOKUP,
        {"TH_uprn": "6001104", "NextCollectionFromDate": "02/10/2026"},
    )


def test_finds_the_uprn_from_postcode_and_house_number():
    data, form = run(
        {ADDRESS_LOOKUP: ADDRESSES, DATES_LOOKUP: DATES}, postcode="E1 6QR", paon="12"
    )
    assert form.calls[1][1]["TH_uprn"] == "6001105"


def test_an_unmatched_house_number_is_an_error_not_another_address():
    with pytest.raises(ValueError, match="No address matching"):
        run({ADDRESS_LOOKUP: ADDRESSES}, postcode="E1 6QR", paon="99")


def test_time_banded_streets_are_collected_daily():
    data, _ = run({TIMEBAND_LOOKUP: TIMEBANDS}, uprn="6001104")
    assert len(data["bins"]) == 7
    assert data["bins"][0] == {
        "type": "Daily Collection (AM: 7:40am to 9:40am / PM: 6:40pm to 8:40pm)",
        "collectionDate": "02/10/2026",
    }


def test_no_dates_or_time_bands_is_an_error():
    with pytest.raises(ValueError, match="No collection data found"):
        run({}, uprn="6001104")


def test_dates_without_a_year_roll_into_next_year():
    assert with_year("04 January", date(2026, 12, 28)) == date(2027, 1, 4)
    assert with_year("28 December", date(2026, 12, 28)) == date(2026, 12, 28)


def test_29_february_is_found_in_the_next_leap_year():
    assert with_year("29 February", date(2027, 12, 20)) == date(2028, 2, 29)
