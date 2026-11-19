"""Unit tests for the Adur & Worthing bin-collection-row parser.

The council changed the label from "Next collection(s):" to "Next
collection dates:" and switched from a single comma-separated line of
dates to one <br>-separated date per line (#2254). Fixtures below are
reduced from the live page's actual markup, captured via CI.

The page gives dates without a year, and the parser rolls any date more than
30 days in the past into next year, so the fixture dates are built from today.
Fixed dates made these tests fail once the calendar moved past them.
"""

from datetime import date, timedelta
from types import SimpleNamespace

from uk_bin_collection.uk_bin_collection.councils.AdurAndWorthingCouncils import (
    CouncilClass,
)


def _label(day: date) -> str:
    """Write a date the way the council does, e.g. "Monday 26th October"."""
    if 11 <= day.day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day.day % 10, "th")
    return f"{day:%A} {day.day}{suffix} {day:%B}"


def _expected(day: date) -> str:
    return day.strftime("%d/%m/%Y")


def _first_monday() -> date:
    monday = date.today() + timedelta(days=7 - date.today().weekday())
    # The parser reads dates as year 1900, which has no 29 February, so avoid it.
    while any(
        (monday + timedelta(weeks=n)).strftime("%m%d") == "0229" for n in range(6)
    ):
        monday += timedelta(weeks=1)
    return monday


# Fortnightly rounds on alternate Mondays, from the next Monday clear of 29 February.
FIRST_MONDAY = _first_monday()
RECYCLING_DAYS = [FIRST_MONDAY + timedelta(weeks=n) for n in (0, 2)]
GENERAL_RUBBISH_DAYS = [FIRST_MONDAY + timedelta(weeks=n) for n in (1, 3, 5)]

GENERAL_RUBBISH_ROW = f"""
<div class="bin-collection-listing-row row">
  <div class="col-md-12 bg-light mb-2 pb-4">
    <h2 class="mt-2">General rubbish</h2>
    <p><img alt="x"/> Grey bin lid</p>
    <p><strong>Frequency:</strong> Fortnightly collections</p>
    <p><strong>Next collection dates:</strong><br/>{"<br/>".join(map(_label, GENERAL_RUBBISH_DAYS))}</p>
  </div>
</div>
"""

RECYCLING_ROW = f"""
<div class="bin-collection-listing-row row">
  <div class="col-md-12 bg-light mb-2 pb-4">
    <h2 class="mt-2">Recycling</h2>
    <p><strong>Next collection dates:</strong><br/>{"<br/>".join(map(_label, RECYCLING_DAYS))}</p>
  </div>
</div>
"""


def parse_fixture(*rows: str) -> dict:
    page = SimpleNamespace(text=f"<html><body>{''.join(rows)}</body></html>")
    return CouncilClass().parse_data(page)


def test_parses_br_separated_dates_under_the_new_label():
    result = parse_fixture(GENERAL_RUBBISH_ROW)

    assert result == {
        "bins": [
            {"type": "General rubbish", "collectionDate": _expected(day)}
            for day in GENERAL_RUBBISH_DAYS
        ]
    }


def test_multiple_bin_rows_are_all_parsed_and_sorted_together():
    result = parse_fixture(GENERAL_RUBBISH_ROW, RECYCLING_ROW)

    recycling, rubbish = RECYCLING_DAYS, GENERAL_RUBBISH_DAYS
    assert result == {
        "bins": [
            {"type": "Recycling", "collectionDate": _expected(recycling[0])},
            {"type": "General rubbish", "collectionDate": _expected(rubbish[0])},
            {"type": "Recycling", "collectionDate": _expected(recycling[1])},
            {"type": "General rubbish", "collectionDate": _expected(rubbish[1])},
            {"type": "General rubbish", "collectionDate": _expected(rubbish[2])},
        ]
    }


def test_no_rows_at_all_is_a_clear_error():
    try:
        parse_fixture()
        assert False, "expected a ValueError"
    except ValueError as exc:
        assert "No bin collection rows found" in str(exc)
