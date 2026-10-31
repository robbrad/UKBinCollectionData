"""Unit tests for the Chelmsford PDF calendar parser and round lookup.

The calendar fixture is a synthetic pdfplumber page mirroring the council's
2026-27 kerbside calendars: pink month header bars, dark circle markers for
black bin weeks and green square markers for brown bin weeks, with the day
number printed inside each marker.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import ChelmsfordCityCouncil as cc
from uk_bin_collection.uk_bin_collection.councils.ChelmsfordCityCouncil import (
    BLACK_BIN_WEEK,
    BROWN_BIN_WEEK,
    CouncilClass,
    _parse_calendar_pdf,
)

PINK = (0.96, 0.85, 0.91)
GREEN = (0.27, 0.54, 0.15)
DARK = (0.28, 0.28, 0.28)


def _word(text, x0, top, x1=None, bottom=None):
    return {
        "text": text,
        "x0": x0,
        "x1": x1 if x1 is not None else x0 + 8,
        "top": top,
        "bottom": bottom if bottom is not None else top + 8,
    }


def _header(month, year, x0, top):
    rect = {
        "x0": x0, "x1": x0 + 139, "top": top, "bottom": top + 12,
        "width": 139, "height": 12, "non_stroking_color": PINK,
    }
    words = [_word(month, x0 + 40, top + 2, x0 + 75), _word(str(year), x0 + 80, top + 2, x0 + 100)]
    return rect, words


def _marker(kind, number, cx, cy):
    shape = {
        "x0": cx - 7, "x1": cx + 7, "top": cy - 7, "bottom": cy + 7,
        "width": 14, "height": 14,
        "non_stroking_color": GREEN if kind == "brown" else DARK,
    }
    return shape, _word(str(number), cx - 4, cy - 4, cx + 4, cy + 4)


def _fake_pdf(headers, markers):
    rects, curves, words = [], [], []
    for month, year, x0, top in headers:
        rect, w = _header(month, year, x0, top)
        rects.append(rect)
        words += w
    for kind, number, cx, cy in markers:
        shape, w = _marker(kind, number, cx, cy)
        (rects if kind == "brown" else curves).append(shape)
        words.append(w)
    page = MagicMock(rects=rects, curves=curves)
    page.extract_words.return_value = words
    pdf = MagicMock(pages=[page])
    return patch.object(cc.pdfplumber, "open", return_value=pdf)


HEADERS = [
    ("December", 2026, 100, 65),
    ("January", 2027, 400, 65),
    ("December", 2026, 100, 300),  # second grid below, must not steal markers
]


def test_markers_are_mapped_to_dates_and_bin_types():
    markers = [
        ("black", 2, 170, 100),
        ("brown", 9, 170, 120),
        ("black", 14, 470, 100),  # moved to a Thursday, still read by number
    ]
    with _fake_pdf(HEADERS[:2], markers):
        result = _parse_calendar_pdf(b"%PDF")

    assert result == [
        (datetime(2026, 12, 2), BLACK_BIN_WEEK),
        (datetime(2026, 12, 9), BROWN_BIN_WEEK),
        (datetime(2027, 1, 14), BLACK_BIN_WEEK),
    ]


def test_marker_belongs_to_nearest_grid_above_it():
    with _fake_pdf(
        [("November", 2026, 100, 65), ("March", 2027, 100, 300)],
        [("brown", 11, 170, 100), ("brown", 3, 170, 330)],
    ):
        result = _parse_calendar_pdf(b"%PDF")

    assert [d for d, _ in result] == [datetime(2026, 11, 11), datetime(2027, 3, 3)]


def test_no_month_headers_raises():
    with _fake_pdf([], [("black", 2, 170, 100)]):
        with pytest.raises(ValueError, match="No month grids"):
            _parse_calendar_pdf(b"%PDF")


def test_no_markers_raises():
    with _fake_pdf(HEADERS[:1], []):
        with pytest.raises(ValueError, match="No collection markers"):
            _parse_calendar_pdf(b"%PDF")


SEARCH_PAGE = '<input id="14532_keyword">'
RESULTS_PAGE = """
<table class="directories-table__table">
<tr><th>Address</th><th>Waste</th></tr>
<tr><td>29 Example Road, Chelmsford, CM2 7BZ</td>
<td><p>This property is covered by the Wednesday A collection round.</p></td></tr>
</table>
"""
CALENDAR_PAGE_PDF = '<a href="/media/abc/wednesday-a-kerbside-collection-calendar.pdf">Download</a>'
CALENDAR_PAGE_NONE = "<p>No calendar here</p>"


def _response(text="", content=b""):
    r = MagicMock(text=text, content=content)
    r.raise_for_status.return_value = None
    return r


def _run(calendar_page, pdf_bytes=b"%PDF-1.7"):
    session = MagicMock()
    session.get.side_effect = [
        _response(SEARCH_PAGE),
        _response(RESULTS_PAGE),
        _response(calendar_page),
        _response(content=pdf_bytes),
    ]
    with patch.object(cc.requests, "Session", return_value=session):
        return CouncilClass().parse_data("", postcode="CM2 7BZ", paon="29"), session


def test_parse_data_uses_pdf_and_limits_to_next_60_days():
    now = datetime.now()
    in_range = (now.replace(hour=0, minute=0, second=0, microsecond=0), BLACK_BIN_WEEK)
    past = (datetime(2020, 1, 1), BROWN_BIN_WEEK)
    far = (datetime(2099, 1, 1), BROWN_BIN_WEEK)
    with patch.object(cc, "_parse_calendar_pdf", return_value=[past, in_range, far]):
        data, session = _run(CALENDAR_PAGE_PDF)

    assert [b["type"] for b in data["bins"]] == BLACK_BIN_WEEK
    assert {b["collectionDate"] for b in data["bins"]} == {in_range[0].strftime("%d/%m/%Y")}
    assert session.get.call_args_list[3].args[0] == (
        "https://www.chelmsford.gov.uk/media/abc/wednesday-a-kerbside-collection-calendar.pdf"
    )


def test_parse_data_raises_when_no_ics_or_pdf_link():
    with pytest.raises(ValueError, match="ICS or PDF"):
        _run(CALENDAR_PAGE_NONE)


def test_parse_data_raises_when_download_is_not_a_pdf():
    with pytest.raises(ValueError, match="Could not download PDF"):
        _run(CALENDAR_PAGE_PDF, pdf_bytes=b"<html>")
