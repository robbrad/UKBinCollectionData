"""Unit tests for the Adur & Worthing bin-collection-row parser.

The council changed the label from "Next collection(s):" to "Next
collection dates:" and switched from a single comma-separated line of
dates to one <br>-separated date per line (#2254). Fixtures below are
reduced from the live page's actual markup, captured via CI.
"""

from types import SimpleNamespace

from uk_bin_collection.uk_bin_collection.councils.AdurAndWorthingCouncils import (
    CouncilClass,
)

GENERAL_RUBBISH_ROW = """
<div class="bin-collection-listing-row row">
  <div class="col-md-12 bg-light mb-2 pb-4">
    <h2 class="mt-2">General rubbish</h2>
    <p><img alt="x"/> Grey bin lid</p>
    <p><strong>Frequency:</strong> Fortnightly collections</p>
    <p><strong>Next collection dates:</strong><br/>Monday 26th October<br/>Monday 9th November<br/>Monday 23rd November</p>
  </div>
</div>
"""

RECYCLING_ROW = """
<div class="bin-collection-listing-row row">
  <div class="col-md-12 bg-light mb-2 pb-4">
    <h2 class="mt-2">Recycling</h2>
    <p><strong>Next collection dates:</strong><br/>Monday 19th October<br/>Monday 2nd November</p>
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
            {"type": "General rubbish", "collectionDate": "26/10/2026"},
            {"type": "General rubbish", "collectionDate": "09/11/2026"},
            {"type": "General rubbish", "collectionDate": "23/11/2026"},
        ]
    }


def test_multiple_bin_rows_are_all_parsed_and_sorted_together():
    result = parse_fixture(GENERAL_RUBBISH_ROW, RECYCLING_ROW)

    assert result == {
        "bins": [
            {"type": "Recycling", "collectionDate": "19/10/2026"},
            {"type": "General rubbish", "collectionDate": "26/10/2026"},
            {"type": "Recycling", "collectionDate": "02/11/2026"},
            {"type": "General rubbish", "collectionDate": "09/11/2026"},
            {"type": "General rubbish", "collectionDate": "23/11/2026"},
        ]
    }


def test_no_rows_at_all_is_a_clear_error():
    try:
        parse_fixture()
        assert False, "expected a ValueError"
    except ValueError as exc:
        assert "No bin collection rows found" in str(exc)
