"""Unit tests for the Isle of Wight results-page and PDF calendar parsers.

Both page fixtures are reduced from live captures taken on 2026-10-15:
DETAILS_PAGE from the input.json test address (Orme House Nursery 125,
PO30 1JW) and NO_DETAILS_PAGE from a non-domestic address on the same
street, which the council reports as having no waste collection details.

The calendar fixtures are synthetic pdfplumber pages that mirror the shape of
the council's 2026/27 round calendars, including the split "SEPTEMB"/"ER"
month header and the white bank-holiday cells those PDFs introduced.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import (
    IsleOfWightCouncil as iow,
)
from uk_bin_collection.uk_bin_collection.councils.IsleOfWightCouncil import (
    _extract_collection_day,
    _select_address,
)

NO_DETAILS_PAGE = """
<div class="form-group" id="AddressSearchResults"><br>
<label class="form-label" for="SelectAddress">Select an address</label>
<select class="form-control mb-3" id="SelectAddress" name="SelectAddress">
<option value="">51 addresses found</option>
<option value="100062421733">Newport Health Clinic, Pyle Street, Newport, Isle Of Wight, PO30 1JW</option>
</select>
<h2 class="mt-5">Collection Details</h2>
<p><strong>Sorry, no waste collection details are currently available for this property</strong></p>
</div>
"""

DETAILS_PAGE = """
<div class="form-group" id="AddressSearchResults">
<select class="form-control mb-3" id="SelectAddress" name="SelectAddress">
<option value="">51 addresses found</option>
<option value="100060758089">Orme House Nursery 125, Pyle Street, Newport, Isle Of Wight, PO30 1JW</option>
</select>
<h2 class="mt-5">Collection Details</h2>
<p><strong>Address:</strong> Orme House Nursery 125, Pyle Street, Newport, Isle Of Wight, PO30 1JW</p>
<p><strong>Collection Day:</strong> Friday</p>
<p><strong>Allocated Bin Type: Gull Sacks</strong></p>
<button class="btn btn-lg btn-success mt-3 mb-2"><span class="fa fa-calendar me-2"></span>View Collection Calendar</button>
</div>
"""


def test_no_collection_details_raises_clear_error():
    with pytest.raises(ValueError, match="no waste collection details"):
        _extract_collection_day(NO_DETAILS_PAGE)


def test_collection_day_extracted_from_live_page_shape():
    assert _extract_collection_day(DETAILS_PAGE) == "Friday"


def test_unrecognised_page_raises():
    with pytest.raises(ValueError, match="Could not find collection day"):
        _extract_collection_day("<div><h1>Waste Collection Day</h1></div>")


def test_select_address_matches_paon_and_skips_placeholder():
    options = [
        "51 addresses found",
        "126, Pyle Street, Newport, Isle Of Wight, PO30 1JW",
        "Orme House Nursery 125, Pyle Street, Newport, Isle Of Wight, PO30 1JW",
    ]
    assert _select_address(options, "Orme House Nursery 125") == options[2]
    assert _select_address(options, "126") == options[1]
    assert _select_address(options, None) == options[1]
    assert _select_address(["51 addresses found"], "126") is None


# --- PDF calendar parsing, against a synthetic pdfplumber page ---------------


RECYCLING = (0.584, 0.757, 0.12)
NON_RECYCLABLE = (0.713, 0.713, 0.712)
HEADER = (0.525, 0.628, 0.828)
BANK_HOLIDAY = (1.0, 1.0, 1.0)

PAGE_WIDTH = 420


def _word(text, x0, top, width=5):
    return {"text": text, "x0": x0, "x1": x0 + width, "top": top, "bottom": top + 8}


def _rect(x0, top, colour):
    return {
        "x0": x0 - 2,
        "x1": x0 + 7,
        "top": top - 2,
        "bottom": top + 10,
        "non_stroking_color": colour,
    }


def _page(day_colours, month_words=None, year_word="2026"):
    """October 2026 in the first column; Mondays (5, 12, 19, 26) at x=10."""
    words = list(
        month_words if month_words is not None else [_word("OCTOBER", 10, 140)]
    )
    if year_word:
        words.append(_word(year_word, 16, 140))
    words += [_word(d, 10 + 15 * i, 150) for i, d in enumerate("MTWTFSS")]
    words.append(_word("6", 25, 160))  # a Tuesday, in another weekday column
    rects = []
    for n, (day, colour) in enumerate(day_colours):
        top = 160 + 12 * n
        words.append(_word(str(day), 10, top))
        rects.append(_rect(10, top, colour))
    page = MagicMock(rects=rects, width=PAGE_WIDTH)
    page.extract_text.return_value = "Collection calendar"
    page.extract_words.return_value = words
    return MagicMock(pages=[page])


def _parse(pdf, day="Monday"):
    with patch.object(iow.pdfplumber, "open", return_value=pdf):
        return iow._parse_calendar_pdf("calendar.pdf", day)


def test_pdf_calendar_days_are_classified_by_background_colour():
    pdf = _page([(5, RECYCLING), (12, NON_RECYCLABLE), (19, HEADER), (26, RECYCLING)])
    assert _parse(pdf) == [
        (datetime(2026, 10, 5), "Recycling"),
        (datetime(2026, 10, 12), "Non-recyclable waste"),
        (datetime(2026, 10, 26), "Recycling"),
    ]


def test_bank_holiday_cells_are_skipped_not_an_error():
    """White is the calendar legend's "Bank Holiday" key: no collection."""
    pdf = _page([(5, RECYCLING), (12, BANK_HOLIDAY), (19, NON_RECYCLABLE)])
    assert _parse(pdf) == [
        (datetime(2026, 10, 5), "Recycling"),
        (datetime(2026, 10, 19), "Non-recyclable waste"),
    ]


def test_pdf_calendar_unknown_colour_is_an_error():
    with pytest.raises(ValueError, match="Unknown calendar colour"):
        _parse(_page([(5, (1.0, 0.0, 0.0))]))


def test_pdf_calendar_rejects_unknown_day_and_missing_months():
    with pytest.raises(ValueError, match="Unknown collection day"):
        _parse(_page([]), day="Someday")
    empty = _page([])
    empty.pages[0].extract_words.return_value = []
    with pytest.raises(ValueError, match="No month headers"):
        _parse(empty)


def test_month_grid_outside_the_page_columns_is_ignored():
    """The rotated left-hand prose panel reports negative x coordinates."""
    off_page = _page([(5, RECYCLING)], month_words=[_word("OCTOBER", -350, 140)])
    off_page.pages[0].extract_words.return_value.append(_word("2026", -344, 140))
    with pytest.raises(ValueError, match="No month grids found"):
        _parse(off_page)


# --- month header detection -------------------------------------------------


def test_split_month_header_is_joined():
    """The 2026/27 PDFs emit SEPTEMBER as "SEPTEMB" + "ER" with no gap."""
    words = [
        _word("SEPTEMB", 171, 240, width=44),
        _word("ER", 215, 240, width=12),
        _word("2026", 230, 240),
    ]
    headers = iow._find_month_headers(words)
    assert [(h["month"], h["year"]) for h in headers] == [(9, 2026)]


def test_mixed_case_month_names_in_prose_are_not_headers():
    """ "Runs May 2026 to April 2027" and "the crew may arrive" are prose."""
    words = [
        _word("Runs", 140, 106, width=20),
        _word("May", 165, 106, width=18),
        _word("2026", 185, 106),
        _word("April", 233, 106, width=22),
        _word("2027", 256, 106),
        _word("may", 300, 106, width=16),
        _word("DECEMBER", 173, 342, width=52),
        _word("2026", 227, 342),
    ]
    headers = iow._find_month_headers(words)
    assert [(h["month"], h["year"]) for h in headers] == [(12, 2026)]


def test_year_is_read_per_month_so_calendars_can_span_new_year():
    words = [
        _word("DECEMBER", 173, 342, width=52),
        _word("2026", 227, 342),
        _word("JANUARY", 305, 342, width=43),
        _word("2027", 351, 342),
    ]
    headers = iow._find_month_headers(words)
    assert [(h["month"], h["year"]) for h in headers] == [(12, 2026), (1, 2027)]


def test_missing_years_are_filled_in_from_neighbours():
    headers = [
        {"month": 11, "year": None},
        {"month": 12, "year": 2026},
        {"month": 1, "year": None},
    ]
    iow._assign_missing_years(headers)
    assert [h["year"] for h in headers] == [2026, 2026, 2027]


def test_a_calendar_with_no_years_at_all_is_an_error():
    with pytest.raises(ValueError, match="No year found beside any month header"):
        iow._find_month_headers([_word("OCTOBER", 10, 140)])


def test_column_index_splits_the_page_into_thirds():
    assert iow._column_index(62, PAGE_WIDTH) == 0
    assert iow._column_index(187, PAGE_WIDTH) == 1
    assert iow._column_index(316, PAGE_WIDTH) == 2
    assert iow._column_index(PAGE_WIDTH, PAGE_WIDTH) == 2
    assert iow._column_index(-350, PAGE_WIDTH) == -1
    assert iow._column_index(PAGE_WIDTH + 1, PAGE_WIDTH) == -1


def test_merge_split_words_leaves_separate_words_alone():
    merged = iow._merge_split_words(
        [_word("AUGUST", 53, 240, width=38), _word("2026", 93, 240)]
    )
    assert [w["text"] for w in merged] == ["AUGUST", "2026"]


# --- colour helpers, output shaping and download caching --------------------


def test_colour_helpers():
    assert iow._color_match((0.5, 0.5, 0.5), (0.52, 0.49, 0.5))
    assert not iow._color_match((0.5, 0.5, 0.5), (0.5, 0.5, 0.5, 0.0))
    assert not iow._color_match(None, (0.5, 0.5, 0.5))
    rects = [
        {"x0": 0, "x1": 100, "top": 0, "bottom": 100, "non_stroking_color": HEADER},
        {"x0": 5, "x1": 15, "top": 5, "bottom": 15, "non_stroking_color": RECYCLING},
    ]
    assert iow._get_bg_color(10, 10, rects) == RECYCLING  # smallest enclosing rect
    assert iow._get_bg_color(50, 50, rects) == HEADER
    assert iow._get_bg_color(500, 500, rects) is None


def test_build_bins_drops_past_dates():
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    data = iow._build_bins(
        [
            (today - timedelta(days=1), "Recycling"),
            (today + timedelta(days=6), "Recycling"),
        ]
    )
    assert data == {
        "bins": [
            {
                "type": "Recycling",
                "collectionDate": (today + timedelta(days=6)).strftime("%d/%m/%Y"),
            }
        ]
    }


def test_pdf_download_is_cached_and_validated(tmp_path):
    ok = MagicMock(status_code=200, content=b"%PDF-1.7 ...")
    with patch.object(iow, "PDF_CACHE_DIR", str(tmp_path)), patch.object(
        iow.requests, "get", return_value=ok
    ) as get:
        first = iow._download_pdf_cached(
            "https://digitalservices.iow.gov.uk/content/wasteday/docs/calendars/FridayWest.pdf"
        )
        second = iow._download_pdf_cached(
            "https://digitalservices.iow.gov.uk/content/wasteday/docs/calendars/FridayWest.pdf"
        )
    assert first == second and open(first, "rb").read().startswith(b"%PDF")
    assert get.call_count == 1

    not_pdf = MagicMock(status_code=200, content=b"<html>")
    with patch.object(iow, "PDF_CACHE_DIR", str(tmp_path)), patch.object(
        iow.requests, "get", return_value=not_pdf
    ):
        with pytest.raises(ValueError, match="Could not download PDF"):
            iow._download_pdf_cached("https://digitalservices.iow.gov.uk/other.pdf")


def test_cache_dir_is_under_the_platform_temp_dir():
    """The old hardcoded /tmp resolved to C:\\tmp on Windows."""
    import tempfile

    assert iow.PDF_CACHE_DIR.startswith(tempfile.gettempdir())
