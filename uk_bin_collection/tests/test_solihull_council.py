"""Unit tests for the Solihull Council bin-card parser.

Reported symptom (#2235): "list index out of range" right after the
council added a food caddy card. Most cards show two div.mt-1 rows
("Last collected" and "Next collection"), and the parser indexed the
second one by position. A bin with no collection history yet (e.g. a
newly added food caddy) renders only the "Next collection" row, so
find_all(...)[1] goes out of range for that card.
"""

from types import SimpleNamespace

from uk_bin_collection.uk_bin_collection.councils.SolihullCouncil import (
    CouncilClass,
)

CARD_WITH_HISTORY = """
<div class="mb-4 card">
  <div class="card-title"><h4>Wheelie General waste</h4></div>
  <div class="mt-1">Last collected: <strong>Thursday 11 September 2026</strong></div>
  <div class="mt-1">Next collection: <strong>Thursday 25 September 2026</strong></div>
</div>
"""

CARD_WITHOUT_HISTORY = """
<div class="mb-4 card">
  <div class="card-title"><h4>Food caddy</h4></div>
  <div class="mt-1">Next collection: <strong>Thursday 18 September 2026</strong></div>
</div>
"""


def parse_fixture(*cards: str) -> dict:
    page = SimpleNamespace(text=f"<html><body>{''.join(cards)}</body></html>")
    return CouncilClass().parse_data(page)


def test_parses_a_card_with_last_collected_and_next_collection():
    result = parse_fixture(CARD_WITH_HISTORY)

    assert result == {
        "bins": [
            {"type": "General waste", "collectionDate": "25/09/2026"},
        ]
    }


def test_parses_a_card_with_only_next_collection():
    result = parse_fixture(CARD_WITHOUT_HISTORY)

    assert result == {
        "bins": [
            {"type": "Food caddy", "collectionDate": "18/09/2026"},
        ]
    }


def test_mixed_cards_do_not_crash_and_both_are_returned():
    result = parse_fixture(CARD_WITH_HISTORY, CARD_WITHOUT_HISTORY)

    assert result == {
        "bins": [
            {"type": "Food caddy", "collectionDate": "18/09/2026"},
            {"type": "General waste", "collectionDate": "25/09/2026"},
        ]
    }


def test_a_card_with_no_date_rows_is_skipped_not_a_crash():
    card_no_dates = """
    <div class="mb-4 card">
      <div class="card-title"><h4>Wheelie Garden waste</h4></div>
    </div>
    """
    result = parse_fixture(card_no_dates, CARD_WITH_HISTORY)

    assert result == {
        "bins": [
            {"type": "General waste", "collectionDate": "25/09/2026"},
        ]
    }
