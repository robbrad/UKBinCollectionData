"""Unit tests for the Coventry City Council bin calendar parser."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from uk_bin_collection.uk_bin_collection.councils.CoventryCityCouncil import (
    CouncilClass,
)

MODULE_PATH = "uk_bin_collection.uk_bin_collection.councils.CoventryCityCouncil"

LINK_PAGE_HTML = b"""
<html><body>
<a href="https://www.coventry.gov.uk/WednesdayBbincollectioncalendar">Find out which bin will be collected when and sign up for a free email reminder.</a>
</body></html>
"""

VALID_CALENDAR_HTML = b"""
<html><body>
<div class="editor">
<h2>August 2026</h2>
<table>
<thead><tr><th>Day and date</th><th>Recycling (blue-lidded bin)</th></tr></thead>
<tbody><tr><td>Wednesday 5 August</td><td>Yes</td></tr></tbody>
</table>
</div>
</body></html>
"""

CALENDAR_HTML_EMPTY_HEADING = b"""
<html><body>
<div class="editor">
<h2></h2>
<table>
<thead><tr><th>Day and date</th><th>Recycling (blue-lidded bin)</th></tr></thead>
<tbody><tr><td>Wednesday 5 August</td><td>Yes</td></tr></tbody>
</table>
</div>
</body></html>
"""

CALENDAR_HTML_NO_BIN_HEADERS = b"""
<html><body>
<div class="editor">
<h2>August 2026</h2>
<table>
<thead><tr><th>Day and date</th></tr></thead>
<tbody><tr><td>Wednesday 5 August</td></tr></tbody>
</table>
</div>
</body></html>
"""


def parse_fixture(calendar_html: bytes):
    page = SimpleNamespace(content=LINK_PAGE_HTML)
    calendar_response = SimpleNamespace(content=calendar_html)
    with patch(f"{MODULE_PATH}.requests.get", return_value=calendar_response):
        return CouncilClass().parse_data(page)


def test_parse_data_parses_a_well_formed_calendar():
    result = parse_fixture(VALID_CALENDAR_HTML)

    assert result == {
        "bins": [{"type": "Recycling", "collectionDate": "05/08/2026"}]
    }


def test_parse_data_raises_on_heading_with_no_year():
    with pytest.raises(ValueError, match="heading has no year"):
        parse_fixture(CALENDAR_HTML_EMPTY_HEADING)


def test_parse_data_raises_on_missing_bin_type_headers():
    with pytest.raises(ValueError, match="no bin-type headers found"):
        parse_fixture(CALENDAR_HTML_NO_BIN_HEADERS)
