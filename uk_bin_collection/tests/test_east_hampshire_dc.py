"""East Hampshire's calendar is four month columns wide, not one.

A single text line in the PDF carries days for four different months, so
anything that reads it line by line files them all under one month. These
tests drive the column and colour logic directly from synthetic pages shaped
like the real one.
"""

from datetime import datetime

from uk_bin_collection.uk_bin_collection.councils.EastHampshireDC import (
    extract_collections,
)

GREEN = (0.248, 0.646, 0.209)
GREY = (0.391, 0.389, 0.387)
ORANGE = (0.971, 0.66, 0.0)

RECYCLING = "Recycling (green bin) and glass box(es)"
RUBBISH = "Rubbish (black bin)"
BANK_HOLIDAY = "Collection (bank holiday change)"

# The four month columns sit at these x positions in the live calendars.
COLUMN_X = [265.0, 348.0, 431.0, 513.0]


def _word(text, x0, top):
    return {
        "text": text,
        "x0": x0,
        "x1": x0 + 6 * len(text),
        "top": top,
        "bottom": top + 9,
    }


def _header(month, year, column, top):
    """A "<MON> <YYYY>" heading at the top of one column."""
    x = COLUMN_X[column]
    return [_word(month, x, top), _word(str(year), x + 6 * len(month) + 4, top)]


def _day(day, column, top, colour):
    """A day number on a coloured cell."""
    x = COLUMN_X[column] + 10
    word = _word(str(day), x, top)
    rect = {
        "x0": x - 8,
        "x1": x + 20,
        "top": top - 3,
        "bottom": top + 12,
        "non_stroking_color": colour,
    }
    return word, rect


def _page(headers, days):
    """headers is already a flat list of word dicts (callers splat _header)."""
    words, rects = list(headers), []
    for word, rect in days:
        words.append(word)
        rects.append(rect)
    return words, rects


def test_each_column_gets_its_own_month_and_year():
    # The exact shape of the live header row: four months, two calendar years.
    headers = [
        *_header("OCT", 2025, 0, 95),
        *_header("JAN", 2026, 1, 95),
        *_header("APR", 2026, 2, 95),
        *_header("JUL", 2026, 3, 95),
    ]
    days = [
        _day(2, 0, 108, GREEN),
        _day(5, 1, 108, GREY),
        _day(9, 2, 108, GREEN),
        _day(16, 3, 108, GREY),
    ]
    result = extract_collections(*_page(headers, days))

    assert result == [
        (RECYCLING, datetime(2025, 10, 2)),
        (RUBBISH, datetime(2026, 1, 5)),
        (RECYCLING, datetime(2026, 4, 9)),
        (RUBBISH, datetime(2026, 7, 16)),
    ]
    # Four days on one row, four different months - the thing the old
    # line-by-line parser could not do.
    assert len({d.month for _, d in result}) == 4


def test_the_year_comes_from_the_header_not_from_today():
    # The old parser stamped datetime.now().year on every date, which put the
    # whole of the previous autumn a year into the future.
    headers = [*_header("OCT", 2025, 0, 95)]
    days = [_day(2, 0, 108, GREEN)]
    ((_, date),) = extract_collections(*_page(headers, days))

    assert date == datetime(2025, 10, 2)


def test_colours_map_to_the_legend():
    headers = [*_header("APR", 2026, 0, 95)]
    days = [
        _day(2, 0, 108, GREEN),
        _day(9, 0, 120, GREY),
        _day(16, 0, 132, ORANGE),
    ]
    types = [t for t, _ in extract_collections(*_page(headers, days))]

    assert types == [RECYCLING, RUBBISH, BANK_HOLIDAY]


def test_a_number_that_is_not_on_a_collection_cell_is_ignored():
    # The page is full of stray numbers - "6am", "24/7", "4pm", a calendar
    # number - that sit on no coloured cell at all.
    headers = [*_header("APR", 2026, 0, 95)]
    words, rects = _page(headers, [_day(2, 0, 108, GREEN)])
    words.append(_word("15", COLUMN_X[0] + 10, 140))  # no rect under it
    words.append(_word("6", COLUMN_X[0] + 10, 152))

    result = extract_collections(words, rects)
    assert result == [(RECYCLING, datetime(2026, 4, 2))]


def test_a_cell_in_an_unknown_colour_is_ignored():
    headers = [*_header("APR", 2026, 0, 95)]
    days = [_day(2, 0, 108, GREEN), _day(9, 0, 120, (1.0, 1.0, 1.0))]

    assert extract_collections(*_page(headers, days)) == [
        (RECYCLING, datetime(2026, 4, 2))
    ]


def test_an_impossible_date_is_skipped():
    headers = [*_header("FEB", 2026, 0, 95)]
    days = [_day(30, 0, 108, GREEN), _day(2, 0, 120, GREY)]

    assert extract_collections(*_page(headers, days)) == [
        (RUBBISH, datetime(2026, 2, 2))
    ]


def test_a_two_digit_number_that_is_not_a_day_is_ignored():
    # "2026" is filtered as a year, but a stray two-digit number over 31 - a
    # page reference, a phone fragment - would otherwise become a date.
    headers = [*_header("APR", 2026, 0, 95)]
    days = [_day(45, 0, 108, GREEN), _day(2, 0, 120, GREY)]

    assert extract_collections(*_page(headers, days)) == [
        (RUBBISH, datetime(2026, 4, 2))
    ]


def test_days_above_their_header_are_not_claimed_by_it():
    # Column headers repeat down the page; a day belongs to the header above
    # it, never one further down.
    headers = [*_header("OCT", 2025, 0, 95), *_header("NOV", 2025, 0, 181)]
    days = [_day(30, 0, 150, GREEN), _day(6, 0, 195, GREY)]

    assert extract_collections(*_page(headers, days)) == [
        (RECYCLING, datetime(2025, 10, 30)),
        (RUBBISH, datetime(2025, 11, 6)),
    ]


def test_results_come_back_in_date_order():
    headers = [
        *_header("OCT", 2025, 0, 95),
        *_header("JAN", 2026, 1, 95),
    ]
    # Deliberately out of order on the page.
    days = [_day(5, 1, 120, GREY), _day(2, 0, 108, GREEN)]
    dates = [d for _, d in extract_collections(*_page(headers, days))]

    assert dates == sorted(dates)


def test_a_page_with_no_headers_yields_nothing():
    _, rects = _page([], [_day(2, 0, 108, GREEN)])
    words = [_word("2", COLUMN_X[0] + 10, 108)]

    assert extract_collections(words, rects) == []


# --- the lookups and the flow around the parser ----------------------------

from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import EastHampshireDC as M

MODULE_PATH = "uk_bin_collection.uk_bin_collection.councils.EastHampshireDC"

# Row shape from the iShare LocationSearch response: the uid is first and the
# display name is at index 7.
ROWS = [
    ["10009818305", "12316032", "", "", "", "", "", "Petersfield URC, College Street"],
    ["1710031629", "12316032", "", "", "", "", "", "15 College Street, Petersfield"],
    ["1710031630", "12316032", "", "", "", "", "", "17 College Street, Petersfield"],
]


def _council():
    return M.CouncilClass()


def _location_response(rows):
    r = MagicMock()
    r.json.return_value = {"data": rows}
    r.raise_for_status.return_value = None
    return r


def test_the_property_uid_matches_on_the_house_name():
    with patch(f"{MODULE_PATH}.requests.get", return_value=_location_response(ROWS)):
        assert (
            _council()._get_property_uid("GU31 4AG", "15 College Street")
            == "1710031629"
        )


def test_the_property_uid_falls_back_to_the_first_row():
    with patch(f"{MODULE_PATH}.requests.get", return_value=_location_response(ROWS)):
        assert _council()._get_property_uid("GU31 4AG", None) == "10009818305"


def test_no_properties_for_the_postcode_is_a_clear_error():
    with patch(f"{MODULE_PATH}.requests.get", return_value=_location_response([])):
        with pytest.raises(ValueError, match="No properties found"):
            _council()._get_property_uid("GU31 4AG", None)


def _jsonp(calendar_value):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.text = "jsonp1(%s);" % __import__("json").dumps(
        {"Results": {"Bin_Calendar": {"_Calendar": calendar_value}}}
    )
    return r


def test_the_calendar_url_and_number_come_out_of_the_jsonp():
    url = "http://maps.easthants.gov.uk/JWWCalendars/2026/norse15.pdf"
    with patch(f"{MODULE_PATH}.requests.get", return_value=_jsonp(f"{url}|15")):
        assert _council()._get_calendar("1710031629") == ("15", url)


def test_a_calendar_field_without_a_number_yields_nothing():
    with patch(f"{MODULE_PATH}.requests.get", return_value=_jsonp("no-pipe-here")):
        assert _council()._get_calendar("1710031629") == (None, None)


def test_a_response_that_is_not_jsonp_yields_nothing():
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.text = "not jsonp at all"
    with patch(f"{MODULE_PATH}.requests.get", return_value=r):
        assert _council()._get_calendar("1710031629") == (None, None)


def test_a_calendar_url_that_is_not_a_pdf_is_rejected(tmp_path):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.content = b"<html>404</html>"
    with patch.object(M, "PDF_CACHE_DIR", str(tmp_path)), patch(
        f"{MODULE_PATH}.requests.get", return_value=r
    ):
        with pytest.raises(ValueError, match="did not return a PDF"):
            _council()._parse_pdf("http://example.invalid/x.pdf")


def _run_parse_data(collections, cal=("15", "http://x/y.pdf")):
    with patch.object(
        M.CouncilClass, "_get_property_uid", return_value="uid"
    ), patch.object(M.CouncilClass, "_get_calendar", return_value=cal), patch.object(
        M.CouncilClass, "_parse_pdf", return_value=collections
    ), patch(
        f"{MODULE_PATH}.check_postcode"
    ):
        return _council().parse_data("", postcode="GU31 4AG", paon="15 College Street")


def test_parse_data_keeps_only_future_collections():
    now = datetime.now()
    past = datetime(now.year - 1, 1, 2)
    future = datetime(now.year + 1, 1, 2)
    result = _run_parse_data([(RUBBISH, past), (RECYCLING, future)])

    assert result == {
        "bins": [{"type": RECYCLING, "collectionDate": future.strftime("%d/%m/%Y")}]
    }


def test_a_missing_calendar_is_a_clear_error():
    with pytest.raises(ValueError, match="No calendar found"):
        _run_parse_data([], cal=(None, None))


def test_a_calendar_that_parses_to_nothing_is_a_clear_error():
    with pytest.raises(ValueError, match="No collection dates could be read"):
        _run_parse_data([])


def test_a_calendar_with_only_past_dates_says_it_has_run_out():
    past = datetime(datetime.now().year - 1, 10, 29)
    with pytest.raises(ValueError, match="only runs to"):
        _run_parse_data([(RUBBISH, past)])
