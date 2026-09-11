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
    # 31 August 2026 is the late summer bank holiday, so 17 + 14 would be a
    # day the council does not collect: the bin is left out until the page
    # shows the real date.
    result = parse_fixture(
        "Monday 17 August -", "Monday 24 August -", real_datetime(2026, 8, 22)
    )

    assert result == {"bins": [{"type": "Recycling", "collectionDate": "24/08/2026"}]}


def test_a_rescheduled_date_on_the_page_is_returned_as_is():
    result = parse_fixture(
        "Tuesday 1 September -", "Monday 7 September -", real_datetime(2026, 8, 30)
    )

    assert result["bins"] == [
        {"type": "Rubbish", "collectionDate": "01/09/2026"},
        {"type": "Recycling", "collectionDate": "07/09/2026"},
    ]


def test_roll_forward_crosses_the_year_boundary():
    result = parse_fixture(
        "Monday 21 December -", "Monday 28 December -", real_datetime(2026, 12, 23)
    )

    assert result["bins"] == [
        {"type": "Recycling", "collectionDate": "28/12/2026"},
        {"type": "Rubbish", "collectionDate": "04/01/2027"},
    ]


def test_no_roll_forward_into_christmas_week():
    # 14 + 14 = 28 December 2026, the observed Boxing Day holiday.
    result = parse_fixture(
        "Monday 14 December -", "Monday 21 December -", real_datetime(2026, 12, 19)
    )

    assert result["bins"] == [{"type": "Recycling", "collectionDate": "21/12/2026"}]
