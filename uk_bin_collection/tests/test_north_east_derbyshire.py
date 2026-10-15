"""Unit tests for the North East Derbyshire area-calendar scraper.

The council withdrew the per-address lookup the old Selenium scraper drove
(#1881) and publishes two area calendars as plain HTML instead. The fixture
below reproduces the live page's markup shapes exactly as captured on
2026-10-15: the North dates in `<li>` elements and the South dates in `<p>`
elements, month headings as `<h4>August 2026</h4>` and as `<p>December '26</p>`,
entries whose start date carries neither month nor year, entries that carry an
explicit year, a bank-holiday week shifted a day later, a two-day range, a
range crossing the year boundary, and the "Which calendar do I use?" settlement
lists in which Sutton appears twice.
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from uk_bin_collection.uk_bin_collection.councils.NorthEastDerbyshireDistrictCouncil import (
    CouncilClass,
    parse_calendar,
)

CALENDAR_PAGE = """
<html><body>
<h2>Bin Collection dates</h2>
<div data-rlta-element="accordion">
  <div id="rlta-view-the-north-area-upcoming-collection-dates" role="button">
    <h3 data-rlta-element="heading"> View the North area - Upcoming collection dates</h3>
  </div>
  <div id="rlta-panel-view-the-north-area-upcoming-collection-dates"
       data-rlta-element="panel" hidden="true">
    <div data-rlta-element="panel-content">
      <p>Refuse and Recycling Collections 2026 (North)</p>
      <p><em>You are in the north of the District if you live in the following
      areas: Arkwright, Barlow, Dronfield and Wadshelf.</em></p>
      <h4>November 2026</h4>
      <ul>
        <li>Monday 2nd to Friday 6th November: Black Bin <strong>and Food Caddy collections.</strong></li>
        <li>Monday 9th to Friday 13th November: Burgundy, Green Bin <strong>and Food Caddy collections.</strong></li>
        <li>Monday 23rd to Friday 27th November: Black Bin <strong>and Food Caddy collections.</strong></li>
        <li>Monday 30th November: Burgundy, Green Bin <strong>and Food Caddy collections.</strong></li>
      </ul>
      <p>December '26</p>
      <ul>
        <li>Monday 30th November to Friday 4th December 2026: <strong>Green Bin, Burgundy Bin and Food Caddy collections </strong></li>
        <li>Monday 21st December to Thursday 24th December 2026: <strong>Black Bin and Food Caddy collections</strong></li>
        <li>Friday 25th December to Monday 28th December 2026: <strong>No collections</strong></li>
        <li>Wednesday 30th December 2026 to Friday 1st January 2027: <strong>No collections</strong></li>
      </ul>
      <p>January '27</p>
      <ul>
        <li>Monday 4th January to Friday 15th January 2027: <strong>Black Bin, Burgundy Bin and Food Caddy collections</strong></li>
        <li>Monday 29th November to Tuesday 30th November 2027: <strong>Green Bin, Burgundy Bin and Food Caddy collections </strong></li>
      </ul>
    </div>
  </div>
  <div id="rlta-view-the-south-area-upcoming-collection-dates" role="button">
    <h3 data-rlta-element="heading"> View the South area - Upcoming collection dates</h3>
  </div>
  <div id="rlta-panel-view-the-south-area-upcoming-collection-dates"
       data-rlta-element="panel" hidden="true">
    <div data-rlta-element="panel-content">
      <p>Refuse and Recycling Collections 2026 (South)</p>
      <h4>November 2026</h4>
      <p>Monday 2nd to Friday 6th November: <strong>Burgundy, Green Bin and Food Caddy collections.</strong></p>
      <p>Monday 9th to Friday 13th November: <strong>B lack Bin and Food Caddy collections.</strong></p>
      <p>Monday 30th November: <strong>Black Bin and Food Caddy collections.</strong></p>
      <p>March 27</p>
      <ul>
        <li>Monday 22nd March to Friday 26th March 2027: <strong>Green Bin, Burgundy Bin and Food Caddy collections</strong></li>
        <li>Monday 29th March 2027: <strong>No collections</strong></li>
        <li>Tuesday 30th March to Saturday 3rd April 2027: <strong>Black Bin and Food Caddy collections</strong></li>
      </ul>
    </div>
  </div>
</div>
<h2>Which calendar do I use?</h2>
<h3><a id="north">Calendar A - The North</a></h3>
<ul>
  <li>Arkwright</li>
  <li>Barlow</li>
  <li>Dronfield</li>
  <li>Sutton (smaller 'rural' route vehicle)</li>
  <li>Wadshelf</li>
</ul>
<p>This includes the smaller 'rural' route areas noted above.</p>
<h3><a id="south">Calendar B - The South</a></h3>
<ul>
  <li>Clay Cross</li>
  <li>Hasland</li>
  <li>Sutton</li>
  <li>Wingerworth</li>
</ul>
<p>This does not include residents collected using the smaller 'rural' route
vehicle in the Sutton and Temple Normanton areas.</p>
</body></html>
"""

TODAY = date(2026, 10, 15)


def collections(paon, today=TODAY):
    """Collapse a parse into {date: [bin types]} for readable assertions."""
    grouped = {}
    for entry in parse_calendar(CALENDAR_PAGE, paon, today)["bins"]:
        grouped.setdefault(entry["collectionDate"], []).append(entry["type"])
    return grouped


def test_north_monday_reads_the_north_calendar():
    found = collections("North, Monday")
    assert found["02/11/2026"] == ["Black Bin", "Food Caddy"]
    # Ordinal suffixes and a start date carrying neither month nor year.
    assert found["09/11/2026"] == ["Burgundy Bin", "Food Caddy", "Green Bin"]
    assert found["23/11/2026"] == ["Black Bin", "Food Caddy"]
    # The same week is listed twice, once per month section; dedupe keeps one.
    assert found["30/11/2026"] == ["Burgundy Bin", "Food Caddy", "Green Bin"]


def test_south_paragraph_entries_are_read_and_differ_from_the_north():
    found = collections("South, Monday")
    assert found["02/11/2026"] == ["Burgundy Bin", "Food Caddy", "Green Bin"]
    assert found["30/11/2026"] == ["Black Bin", "Food Caddy"]
    # The council's "B lack Bin" typo still matches.
    assert found["09/11/2026"] == ["Black Bin", "Food Caddy"]


def test_a_settlement_name_selects_its_calendar():
    assert collections("Dronfield, Monday")["02/11/2026"] == [
        "Black Bin",
        "Food Caddy",
    ]
    assert collections("Clay Cross, Monday")["02/11/2026"] == [
        "Burgundy Bin",
        "Food Caddy",
        "Green Bin",
    ]


def test_multi_week_range_yields_every_matching_weekday():
    found = collections("North, Monday")
    both = ["Black Bin", "Burgundy Bin", "Food Caddy"]
    assert found["04/01/2027"] == both
    assert found["11/01/2027"] == both


def test_short_range_covers_only_the_days_it_spans():
    # "Monday 21st December to Thursday 24th December 2026" excludes Friday.
    assert "21/12/2026" in collections("North, Monday")
    assert "25/12/2026" not in collections("North, Friday")
    # "Monday 29th November to Tuesday 30th November 2027" is a two-day range.
    assert "29/11/2027" in collections("North, Monday")
    assert "30/11/2027" in collections("North, Tuesday")
    assert "01/12/2027" not in collections("North, Wednesday")


def test_range_crossing_the_year_boundary_is_dated_correctly():
    # "Wednesday 30th December 2026 to Friday 1st January 2027" is a
    # no-collection week, so nothing from it should appear at all.
    for weekday in ("Wednesday", "Thursday", "Friday"):
        found = collections(f"North, {weekday}")
        assert not any(key.endswith("12/2026") and key[:2] >= "30" for key in found)
        assert "01/01/2027" not in found


def test_bank_holiday_week_shifts_every_household_a_day_later():
    # "Tuesday 30th March to Saturday 3rd April 2027" after a bank holiday.
    assert collections("South, Monday")["30/03/2027"] == ["Black Bin", "Food Caddy"]
    assert collections("South, Friday")["03/04/2027"] == ["Black Bin", "Food Caddy"]
    # The normal week before it is not shifted.
    assert "22/03/2027" in collections("South, Monday")


def test_past_collections_are_dropped():
    found = collections("North, Monday", today=date(2026, 11, 24))
    assert "02/11/2026" not in found
    assert "30/11/2026" in found


def test_no_collection_weeks_are_skipped():
    assert "28/12/2026" not in collections("North, Monday")


def test_settlement_on_both_calendars_is_rejected():
    with pytest.raises(ValueError, match="on both of North East Derbyshire's"):
        parse_calendar(CALENDAR_PAGE, "Sutton, Monday", TODAY)


def test_unknown_area_lists_the_accepted_values():
    with pytest.raises(ValueError) as excinfo:
        parse_calendar(CALENDAR_PAGE, "Narnia, Monday", TODAY)
    message = str(excinfo.value)
    assert "not a North East Derbyshire collection area" in message
    assert "Clay Cross" in message and "Dronfield" in message


@pytest.mark.parametrize("paon", ["North, Funday", "North", "", None, "Monday"])
def test_unreadable_input_is_rejected(paon):
    with pytest.raises(ValueError) as excinfo:
        parse_calendar(CALENDAR_PAGE, paon, TODAY)
    assert "house number field" in str(excinfo.value)


def test_weekday_abbreviations_and_order_are_accepted():
    assert collections("mon, north") == collections("North, Monday")


def test_saturday_is_not_an_accepted_collection_day():
    # Nobody in the district has a normal Saturday collection; a Saturday date
    # only arises as a bank-holiday week's shifted Friday.
    with pytest.raises(ValueError, match="Accepted weekdays"):
        parse_calendar(CALENDAR_PAGE, "North, Saturday", TODAY)


def test_an_exhausted_calendar_raises():
    with pytest.raises(ValueError, match="No upcoming north collections"):
        parse_calendar(CALENDAR_PAGE, "North, Monday", date(2028, 1, 1))


def test_parse_data_fetches_the_calendar_page():
    url = "https://www.ne-derbyshire.gov.uk/bins-and-recycling/bin-collection-dates"
    response = SimpleNamespace(text=CALENDAR_PAGE, raise_for_status=lambda: None)
    with patch(
        "uk_bin_collection.uk_bin_collection.councils."
        "NorthEastDerbyshireDistrictCouncil.requests.get",
        return_value=response,
    ) as mock_get:
        data = CouncilClass().parse_data("", url=url, paon="North, Monday")

    assert {"type": "Black Bin", "collectionDate": "04/01/2027"} in data["bins"]
    assert mock_get.call_args.args[0] == url
    assert mock_get.call_args.kwargs["headers"]["User-Agent"].startswith(
        "uk-bin-collection/"
    )
