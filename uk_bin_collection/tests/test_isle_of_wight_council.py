"""Unit tests for the Isle of Wight results-page parser.

The "no details" fixture is reduced from the live page captured via CI for
the input.json test address (County Hall, PO30 1UD), which the council
reports as having no waste collection details. DETAILS_PAGE is synthetic and
only mirrors the markup shape the parser expects (not a live capture).
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import (
    IsleOfWightCouncil as iow,
)
from uk_bin_collection.uk_bin_collection.councils.IsleOfWightCouncil import (
    _extract_collection_info,
    _select_address,
)

NO_DETAILS_PAGE = """
<div class="form-group" id="AddressSearchResults"><br>
<label class="form-label" for="SelectAddress">Select an address</label>
<select class="form-control mb-3" id="SelectAddress" name="SelectAddress">
<option value="">1 addresses found</option>
<option value="010003317358">County Hall, High Street, Newport, Isle Of Wight, PO30 1UD</option>
</select>
<h2 class="mt-5">Collection Details</h2>
<p><strong>Sorry, no waste collection details are currently available for this property</strong></p>
</div>
"""

DETAILS_PAGE = """
<div id="AddressSearchResults">
<h2 class="mt-5">Collection Details</h2>
<p><strong>Collection Day:</strong> Tuesday</p>
<a class="download" href="/media/calendar.pdf">Download calendar</a>
</div>
"""


def test_no_collection_details_raises_clear_error():
    with pytest.raises(ValueError, match="no waste collection details"):
        _extract_collection_info(NO_DETAILS_PAGE)


def test_collection_day_and_pdf_url_extracted():
    day, pdf_url = _extract_collection_info(DETAILS_PAGE)
    assert day == "Tuesday"
    assert pdf_url == "https://www.iow.gov.uk/media/calendar.pdf"


def test_select_address_matches_paon_and_skips_placeholder():
    options = [
        "1 addresses found",
        "County Hall, High Street, Newport, Isle Of Wight, PO30 1UD",
    ]
    assert _select_address(options, "County Hall") == options[1]
    assert _select_address(options, None) == options[1]


# --- PDF calendar parsing, against a synthetic pdfplumber page ---------------


RECYCLING = (0.584, 0.757, 0.12)
NON_RECYCLABLE = (0.713, 0.713, 0.712)
HEADER = (0.525, 0.628, 0.828)


def _word(text, x0, top):
    return {"text": text, "x0": x0, "x1": x0 + 5, "top": top, "bottom": top + 8}


def _rect(x0, top, colour):
    return {
        "x0": x0 - 2,
        "x1": x0 + 7,
        "top": top - 2,
        "bottom": top + 10,
        "non_stroking_color": colour,
    }


def _page(day_colours):
    """October 2026 in the first column; Mondays (5, 12, 19, 26) at x=10."""
    words = [_word("OCTOBER", 10, 140)]
    words += [_word(d, 10 + 15 * i, 150) for i, d in enumerate("MTWTFSS")]
    words.append(_word("6", 25, 160))  # a Tuesday, in another weekday column
    rects = []
    for n, (day, colour) in enumerate(day_colours):
        top = 160 + 12 * n
        words.append(_word(str(day), 10, top))
        rects.append(_rect(10, top, colour))
    page = MagicMock(rects=rects)
    page.extract_text.return_value = "Collection calendar 2026 2027"
    page.extract_words.return_value = words
    return MagicMock(pages=[page])


def test_pdf_calendar_days_are_classified_by_background_colour():
    pdf = _page([(5, RECYCLING), (12, NON_RECYCLABLE), (19, HEADER), (26, RECYCLING)])
    with patch.object(iow.pdfplumber, "open", return_value=pdf):
        result = iow._parse_calendar_pdf("calendar.pdf", "Monday")
    assert result == [
        (datetime(2026, 10, 5), "Recycling"),
        (datetime(2026, 10, 12), "Non-recyclable waste"),
        (datetime(2026, 10, 26), "Recycling"),
    ]


def test_pdf_calendar_unknown_colour_is_an_error():
    with patch.object(
        iow.pdfplumber, "open", return_value=_page([(5, (1.0, 0.0, 0.0))])
    ):
        with pytest.raises(ValueError, match="Unknown calendar colour"):
            iow._parse_calendar_pdf("calendar.pdf", "Monday")


def test_pdf_calendar_rejects_unknown_day_and_missing_months():
    with patch.object(iow.pdfplumber, "open", return_value=_page([])):
        with pytest.raises(ValueError, match="Unknown collection day"):
            iow._parse_calendar_pdf("calendar.pdf", "Someday")
    empty = _page([])
    empty.pages[0].extract_words.return_value = []
    with patch.object(iow.pdfplumber, "open", return_value=empty):
        with pytest.raises(ValueError, match="No month headers"):
            iow._parse_calendar_pdf("calendar.pdf", "Monday")


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
        first = iow._download_pdf_cached("https://www.iow.gov.uk/cal.pdf")
        second = iow._download_pdf_cached("https://www.iow.gov.uk/cal.pdf")
    assert first == second and open(first, "rb").read().startswith(b"%PDF")
    assert get.call_count == 1

    not_pdf = MagicMock(status_code=200, content=b"<html>")
    with patch.object(iow, "PDF_CACHE_DIR", str(tmp_path)), patch.object(
        iow.requests, "get", return_value=not_pdf
    ):
        with pytest.raises(ValueError, match="Could not download PDF"):
            iow._download_pdf_cached("https://www.iow.gov.uk/other.pdf")
