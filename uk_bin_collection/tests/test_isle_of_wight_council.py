"""Unit tests for the Isle of Wight results-page parser.

The "no details" fixture is reduced from the live page captured via CI for
the input.json test address (County Hall, PO30 1UD), which the council
reports as having no waste collection details. DETAILS_PAGE is synthetic and
only mirrors the markup shape the parser expects (not a live capture).
"""

import pytest

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
