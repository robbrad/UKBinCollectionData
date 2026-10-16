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
