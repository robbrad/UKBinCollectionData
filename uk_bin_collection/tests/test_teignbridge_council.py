"""Unit tests for the Teignbridge Council collection-card parser."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from uk_bin_collection.uk_bin_collection.councils.TeignbridgeCouncil import (
    CouncilClass,
)

MODULE_PATH = "uk_bin_collection.uk_bin_collection.councils.TeignbridgeCouncil"

# Trimmed from the live GetCollections fragment for UPRN 100040338776. Note the
# weekday sits in a nested span with no separator, so the heading's text reads
# "15 October 2026Thursday".
RESULTS_HTML = """
<h2 class="findOutH2" id="bfAddr">4 Admirals Walk, TEIGNMOUTH, TQ14 9NG</h2>
<h3 class="binCollectionH3">15 October 2026
<span class="binDayDescriptor">Thursday</span></h3>
<div class="binInfoContainer">
<div class="binInfoLine"><span class="binImg"><a href="/foodwaste"></a></span> Food waste container</div>
<div class="binInfoLine"><span class="binImg"><a href="/blackbox"></a></span> Black box</div>
<div class="binInfoLine"><span class="binImg"><a href="/gardenwaste"></a></span> Garden waste - green bin</div>
</div>
<h3 class="binCollectionH3">22 October 2026
<span class="binDayDescriptor">Thursday</span></h3>
<div class="binInfoContainer">
<div class="binInfoLine"><span class="binImg"><a href="/foodwaste"></a></span> Food waste container</div>
<div class="binInfoLine"><span class="binImg"><a href="/blackbin"></a></span> Refuse - black bin</div>
</div>
"""

NO_DETAILS_HTML = (
    "<span>Sorry, but we cannot find any collection details for this property.</span>"
)


def parse_fixture(html: str, status_code: int = 200):
    response = SimpleNamespace(
        text=html, status_code=status_code, raise_for_status=lambda: None
    )
    with patch(f"{MODULE_PATH}.requests.get", return_value=response):
        return CouncilClass().parse_data("", uprn="100040338776")


def test_parse_data_pairs_each_day_with_its_own_bin_types():
    assert parse_fixture(RESULTS_HTML) == {
        "bins": [
            {"type": "Food waste container", "collectionDate": "15/10/2026"},
            {"type": "Black box", "collectionDate": "15/10/2026"},
            {"type": "Garden waste - green bin", "collectionDate": "15/10/2026"},
            {"type": "Food waste container", "collectionDate": "22/10/2026"},
            {"type": "Refuse - black bin", "collectionDate": "22/10/2026"},
        ]
    }


def test_parse_data_queries_the_umbraco_surface_controller_with_the_uprn():
    response = SimpleNamespace(
        text=RESULTS_HTML, status_code=200, raise_for_status=lambda: None
    )
    with patch(f"{MODULE_PATH}.requests.get", return_value=response) as mock_get:
        CouncilClass().parse_data("", uprn="100040338776")

    url = mock_get.call_args.args[0]
    assert url.endswith("/umbraco/surface/bincollection/GetCollections")
    assert mock_get.call_args.kwargs["params"] == {"uprn": "100040338776"}
    # The Azure gateway 403s the default python-requests User-Agent.
    assert "uk-bin-collection/" in mock_get.call_args.kwargs["headers"]["User-Agent"]


def test_an_unknown_uprn_is_a_clear_error_not_an_index_error():
    # The old scraper hit "list index out of range" here, because the 404 page
    # it was really fetching had one unrelated <h3> and no bin containers.
    with pytest.raises(ValueError, match="no collection days"):
        parse_fixture(NO_DETAILS_HTML)


def test_a_403_is_reported_as_a_block_not_a_bad_uprn():
    with pytest.raises(ConnectionError, match="403 Forbidden"):
        parse_fixture("", status_code=403)


def test_parse_data_ignores_headings_outside_the_collection_cards():
    # A stray <h3> elsewhere on the page must not be treated as a date; the
    # old scraper's bare find_all("h3") was what made that fatal.
    html = '<h3 class="pageH3">Getting the right result</h3>' + RESULTS_HTML
    assert len(parse_fixture(html)["bins"]) == 5
