"""Unit tests for the Herefordshire Council collection parser."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from uk_bin_collection.uk_bin_collection.councils.HerefordshireCouncil import (
    CouncilClass,
)

MODULE_PATH = "uk_bin_collection.uk_bin_collection.councils.HerefordshireCouncil"

# Trimmed from the live page for UPRN 200002618844. The "Garden waste - brown
# bin" heading has no dates of its own when the property isn't subscribed - the
# next sibling list belongs to the "Calendar" heading instead.
RESULTS_HTML = """
<html>
  <body>
    <h2 class="c-supplement__heading">Your next collection days</h2>
    <h3 class="c-supplement__heading">General rubbish - black bin</h3>
    <ul class="c-supplement__list">
      <li>Tuesday 27 October 2026 (next collection)</li>
      <li>Tuesday 10 November 2026 (subsequent collection)</li>
    </ul>
    <h3 class="c-supplement__heading">Recycling - green bin</h3>
    <ul class="c-supplement__list">
      <li>Tuesday 20 October 2026 (next collection)</li>
      <li>Tuesday 3 November 2026 (subsequent collection)</li>
    </ul>
    <h3 class="c-supplement__heading">Garden waste - brown bin</h3>
    <h3 class="c-supplement__heading">Calendar</h3>
    <ul class="c-supplement__list">
      <li><a href="/calendar.pdf">Download your 2026-2027 calendar</a></li>
    </ul>
  </body>
</html>
"""


def parse_fixture(html: str, status_code: int = 200):
    response = SimpleNamespace(text=html, status_code=status_code)
    with patch(f"{MODULE_PATH}.requests.get", return_value=response):
        return CouncilClass().parse_data("", uprn="200002618844")


def test_parse_data_returns_each_subscribed_bin_with_its_next_date():
    assert parse_fixture(RESULTS_HTML) == {
        "bins": [
            {"type": "General rubbish - black bin", "collectionDate": "27/10/2026"},
            {"type": "Recycling - green bin", "collectionDate": "20/10/2026"},
        ]
    }


def test_parse_data_sends_a_non_default_user_agent():
    # The council's Azure Application Gateway 403s the default
    # python-requests User-Agent, so the header must always be sent.
    response = SimpleNamespace(text=RESULTS_HTML, status_code=200)
    with patch(f"{MODULE_PATH}.requests.get", return_value=response) as mock_get:
        CouncilClass().parse_data("", uprn="200002618844")

    headers = mock_get.call_args.kwargs["headers"]
    assert "uk-bin-collection/" in headers["User-Agent"]
    assert "python-requests" not in headers["User-Agent"]


def test_a_403_is_reported_as_a_block_not_a_bad_uprn():
    with pytest.raises(ConnectionError, match="403 Forbidden"):
        parse_fixture("", status_code=403)


def test_a_page_without_the_results_heading_is_an_unknown_uprn():
    html = RESULTS_HTML.replace("Your next collection days", "Check your bin day")
    with pytest.raises(ValueError, match="Address/UPRN not found"):
        parse_fixture(html)


def test_an_unsubscribed_garden_bin_is_skipped_not_parsed_as_a_date():
    # Regression guard: the brown-bin heading's "next" list is the calendar
    # link, which would explode in strptime if it were treated as a date.
    types = [bin["type"] for bin in parse_fixture(RESULTS_HTML)["bins"]]
    assert "Garden waste - brown bin" not in types
