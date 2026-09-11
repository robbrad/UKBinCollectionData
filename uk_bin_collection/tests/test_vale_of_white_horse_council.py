"""Unit tests for the Vale of White Horse fortnightly roll-forward.

The council page publishes the current fortnight's pair of collections rather
than the next occurrence of each bin, so the scraper rolls a past date forward
by 14 days - except into a week with a bank holiday, when the council collects
on a different day and only the page knows which.
"""

from datetime import datetime as real_datetime
from types import SimpleNamespace
from unittest.mock import patch

from uk_bin_collection.uk_bin_collection.councils.ValeofWhiteHorseCouncil import (
    CouncilClass,
)

MODULE_PATH = "uk_bin_collection.uk_bin_collection.councils.ValeofWhiteHorseCouncil"

PAGE = """
<html><body>
  <div class="bintxt">It's rubbish week</div>
  <div class="binextra"><span>{rubbish}</span><span>grey bin, small electrical items and food bin</span></div>
  <div class="bintxt">It's recycling week</div>
  <div class="binextra"><span>{recycling}</span><span>food bin, green bin, textiles and garden waste bin</span></div>
</body></html>
"""


def parse_fixture(rubbish: str, recycling: str, now: real_datetime) -> dict:
    """Run the parser against a page showing the given two panels, on `now`."""

    class FrozenDatetime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    response = SimpleNamespace(text=PAGE.format(rubbish=rubbish, recycling=recycling))
    with patch(f"{MODULE_PATH}.requests.Session") as session, patch(
        f"{MODULE_PATH}.datetime", FrozenDatetime
    ):
        session.return_value.get.return_value = response
        return CouncilClass().parse_data("", uprn="100120000000")


def test_a_bin_collected_earlier_this_fortnight_rolls_forward_14_days():
    """A past date in a holiday-free fortnight is advanced by 14 days."""
    result = parse_fixture(
        "Monday 3 August -", "Monday 10 August -", real_datetime(2026, 8, 8)
    )

    assert result == {
        "bins": [
            {"type": "Recycling", "collectionDate": "10/08/2026"},
            {"type": "Rubbish", "collectionDate": "17/08/2026"},
        ]
    }


def test_no_roll_forward_into_a_bank_holiday_week():
    """31 August 2026 is the late summer bank holiday, so 17 + 14 would be a
    day the council does not collect: the bin is left out until the page shows
    the real date."""
    result = parse_fixture(
        "Monday 17 August -", "Monday 24 August -", real_datetime(2026, 8, 22)
    )

    assert result == {"bins": [{"type": "Recycling", "collectionDate": "24/08/2026"}]}


def test_a_rescheduled_date_on_the_page_is_returned_as_is():
    """A date the page states outright is the source of truth, holiday or not."""
    result = parse_fixture(
        "Tuesday 1 September -", "Monday 7 September -", real_datetime(2026, 8, 30)
    )

    assert result["bins"] == [
        {"type": "Rubbish", "collectionDate": "01/09/2026"},
        {"type": "Recycling", "collectionDate": "07/09/2026"},
    ]


def test_no_roll_forward_into_the_january_slippage_weeks():
    """21 + 14 = 4 January 2027, a week with no bank holiday in it, but the
    council's leaflet collects that Monday's bins on Wednesday 6 January:
    Christmas slippage outlasts the holidays, so January is left to the page."""
    result = parse_fixture(
        "Monday 21 December -", "Monday 28 December -", real_datetime(2026, 12, 23)
    )

    assert result["bins"] == [{"type": "Recycling", "collectionDate": "28/12/2026"}]


def test_a_december_date_seen_in_january_belongs_to_last_year():
    """On 9 January 2027 the page still shows Monday 28 December, which is
    28 December 2026, not a collection eleven months away. It rolls forward
    into the slippage weeks and is left out; 4 January rolls to 18 January,
    the first normal week, and is returned."""
    result = parse_fixture(
        "Monday 28 December -", "Monday 4 January -", real_datetime(2027, 1, 9)
    )

    assert result["bins"] == [{"type": "Recycling", "collectionDate": "18/01/2027"}]


def test_no_roll_forward_into_christmas_week():
    """14 + 14 = 28 December 2026, the observed Boxing Day holiday."""
    result = parse_fixture(
        "Monday 14 December -", "Monday 21 December -", real_datetime(2026, 12, 19)
    )

    assert result["bins"] == [{"type": "Recycling", "collectionDate": "21/12/2026"}]


def test_roll_forward_through_a_bank_holiday_week_to_a_normal_one():
    """A page still showing 17 August on 2 September rolls through the bank
    holiday week to 14 September, which is right: the holiday shifts the
    collections of its own week and the fortnight then resumes as usual."""
    result = parse_fixture(
        "Monday 17 August -", "Monday 24 August -", real_datetime(2026, 9, 2)
    )

    assert result["bins"] == [
        {"type": "Recycling", "collectionDate": "07/09/2026"},
        {"type": "Rubbish", "collectionDate": "14/09/2026"},
    ]
