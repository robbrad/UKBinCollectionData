from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import ChelmsfordCityCouncil as cc
from uk_bin_collection.uk_bin_collection.councils.ChelmsfordCityCouncil import (
    BLACK_BIN_WEEK,
    BROWN_BIN_WEEK,
    CouncilClass,
    _extract_candidates,
    _match_address,
    _parse_calendar_pdf,
)

FIXTURE_PDF = (
    Path(__file__).parent / "fixtures" / "chelmsford_tuesday_a_kerbside_calendar.pdf"
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
        "x0": x0,
        "x1": x0 + 139,
        "top": top,
        "bottom": top + 12,
        "width": 139,
        "height": 12,
        "non_stroking_color": PINK,
    }
    words = [
        _word(month, x0 + 40, top + 2, x0 + 75),
        _word(str(year), x0 + 80, top + 2, x0 + 100),
    ]
    return rect, words


def _marker(kind, number, cx, cy):
    shape = {
        "x0": cx - 7,
        "x1": cx + 7,
        "top": cy - 7,
        "bottom": cy + 7,
        "width": 14,
        "height": 14,
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
<tr><td>1 Celeborn Street, Chelmsford, CM3 7AE</td>
<td><p>This property is covered by the Tuesday B collection round.</p></td></tr>
</table>
"""
CALENDAR_PAGE_PDF = (
    '<a href="/media/abc/tuesday-b-kerbside-collection-calendar.pdf">Download</a>'
)
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
        return CouncilClass().parse_data("", postcode="CM3 7AE", paon="1"), session


def test_parse_data_uses_pdf_and_limits_to_next_60_days():
    now = datetime.now()
    in_range = (now.replace(hour=0, minute=0, second=0, microsecond=0), BLACK_BIN_WEEK)
    past = (datetime(2020, 1, 1), BROWN_BIN_WEEK)
    far = (datetime(2099, 1, 1), BROWN_BIN_WEEK)
    with patch.object(cc, "_parse_calendar_pdf", return_value=[past, in_range, far]):
        data, session = _run(CALENDAR_PAGE_PDF)

    assert [b["type"] for b in data["bins"]] == BLACK_BIN_WEEK
    assert {b["collectionDate"] for b in data["bins"]} == {
        in_range[0].strftime("%d/%m/%Y")
    }
    assert session.get.call_args_list[3].args[0] == (
        "https://www.chelmsford.gov.uk/media/abc/tuesday-b-kerbside-collection-calendar.pdf"
    )


def test_parse_data_raises_when_no_ics_or_pdf_link():
    with pytest.raises(ValueError, match="ICS or PDF"):
        _run(CALENDAR_PAGE_NONE)


def test_parse_data_raises_when_download_is_not_a_pdf():
    with pytest.raises(ValueError, match="Could not download PDF"):
        _run(CALENDAR_PAGE_PDF, pdf_bytes=b"<html>")


# --- Real PDF fixture -------------------------------------------------------
# chelmsford_tuesday_a_kerbside_calendar.pdf is the council's published
# "Tuesday A" calendar (Nov 2026 - Oct 2027), reduced to its single page. It is a
# per-round calendar, so it holds no property data. If the council changes the
# marker colours, this is the test that fails; re-measure them with
# pdfplumber (page.rects / page.curves, `non_stroking_color`) and update the
# constants at the top of ChelmsfordCityCouncil.py.


def test_real_pdf_fixture_is_parsed_without_mocks():
    results = _parse_calendar_pdf(FIXTURE_PDF.read_bytes())

    assert len(results) == 52
    assert results[0] == (datetime(2026, 11, 3), BLACK_BIN_WEEK)
    assert results[1] == (datetime(2026, 11, 10), BROWN_BIN_WEEK)
    assert results[-1][0] == datetime(2027, 10, 26)
    # Weeks alternate black / brown for the whole year.
    assert [bins for _, bins in results] == [BLACK_BIN_WEEK, BROWN_BIN_WEEK] * 26
    dates = [d for d, _ in results]
    assert dates == sorted(dates) and len(set(dates)) == 52


def test_real_pdf_fixture_picks_up_bank_holiday_moves():
    moved = {
        d: bins
        for d, bins in _parse_calendar_pdf(FIXTURE_PDF.read_bytes())
        if d.weekday() != 1
    }

    assert set(moved) == {
        datetime(2026, 12, 30),
        datetime(2027, 1, 7),
        datetime(2027, 1, 13),
    }


# --- Address matching -------------------------------------------------------

ROUND = "https://www.chelmsford.gov.uk/bins-and-recycling/check-your-collection-day/tuesday-b-collection-calendar/"
ADDRESSES = [
    "1 Celeborn Street, South Woodham Ferrers, Chelmsford, CM3 7AE",
    "1A Celeborn Street, South Woodham Ferrers, Chelmsford, CM3 7AE",
    "11 Celeborn Street, South Woodham Ferrers, Chelmsford, CM3 7AE",
    "21 Celeborn Street, South Woodham Ferrers, Chelmsford, CM3 7AE",
    "Flat 1, 5 Celeborn Street, South Woodham Ferrers, Chelmsford, CM3 7AE",
    "Flat 2, 5 Celeborn Street, South Woodham Ferrers, Chelmsford, CM3 7AE",
]
CANDIDATES = [{"address": a, "calendar_url": ROUND} for a in ADDRESSES]


@pytest.mark.parametrize(
    "paon, expected",
    [
        ("1", ADDRESSES[0]),  # not 11, 21 or 1A
        ("11", ADDRESSES[2]),
        ("1A", ADDRESSES[1]),
        ("1a", ADDRESSES[1]),
        (" 21 ", ADDRESSES[3]),
        ("Flat 2", ADDRESSES[5]),
        ("1 Celeborn Street", ADDRESSES[0]),
        (ADDRESSES[2], ADDRESSES[2]),  # the full address copied from the council site
    ],
)
def test_match_address_uses_start_of_address_as_whole_word(paon, expected):
    assert _match_address(CANDIDATES, paon)["address"] == expected


@pytest.mark.parametrize("paon", ["Celeborn", "7AE", "2", "South Woodham"])
def test_match_address_does_not_match_inside_the_address(paon):
    with pytest.raises(ValueError, match="No address starting with"):
        _match_address(CANDIDATES, paon)


def test_match_address_zero_matches_lists_the_candidates():
    with pytest.raises(ValueError) as exc:
        _match_address(CANDIDATES, "99")
    assert all(a in str(exc.value) for a in ADDRESSES)


def test_match_address_multiple_matches_lists_only_the_matches():
    with pytest.raises(ValueError, match="matches 2 addresses") as exc:
        _match_address(CANDIDATES, "Flat")
    assert ADDRESSES[4] in str(exc.value) and ADDRESSES[5] in str(exc.value)
    assert ADDRESSES[0] not in str(exc.value)


def test_match_address_ignores_duplicate_rows():
    assert _match_address(CANDIDATES + CANDIDATES[:1], "1")["address"] == ADDRESSES[0]


@pytest.mark.parametrize("paon", [None, ""])
def test_match_address_requires_a_paon(paon):
    with pytest.raises(ValueError, match="Invalid house number"):
        _match_address(CANDIDATES, paon)


def test_extract_candidates_from_table_and_details():
    from bs4 import BeautifulSoup

    table = BeautifulSoup(
        "<table><tr><th>Address</th><th>Waste</th></tr>"
        "<tr><td>1 A St</td><td>This property is covered by the Friday A collection round.</td></tr>"
        "<tr><td>2 A St</td><td>We are currently unable to display the collections.</td></tr></table>",
        "html.parser",
    )
    assert _extract_candidates(table) == [
        {"address": "1 A St", "calendar_url": ROUND.replace("tuesday-b", "friday-a")},
        {"address": "2 A St", "calendar_url": None},
    ]
    details = BeautifulSoup(
        '<details><summary>3 A St</summary><a href="/x/monday-b-collection-calendar/">cal</a></details>',
        "html.parser",
    )
    assert _extract_candidates(details) == [
        {
            "address": "3 A St",
            "calendar_url": "https://www.chelmsford.gov.uk/x/monday-b-collection-calendar/",
        }
    ]


def test_parse_data_raises_when_the_address_has_no_round():
    results = RESULTS_PAGE.replace(
        "This property is covered by the Tuesday B collection round.",
        "We are currently unable to display the collections.",
    )
    session = MagicMock()
    session.get.side_effect = [_response(SEARCH_PAGE), _response(results)]
    with patch.object(cc.requests, "Session", return_value=session):
        with pytest.raises(ValueError, match="no collection round"):
            CouncilClass().parse_data("", postcode="CM3 7AE", paon="1")
