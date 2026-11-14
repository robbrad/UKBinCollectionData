"""Regression tests for Charnwood's legacy property URL configuration."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import CharnwoodBoroughCouncil

MODULE_PATH = "uk_bin_collection.uk_bin_collection.councils.CharnwoodBoroughCouncil"
PROPERTY_URL = (
    "https://my.charnwood.gov.uk/location?put=cbc12345678901"
    "&rememberme=0&redirect=%2F"
)
COLLECTION_HTML = """
<ul class="refuse">
  <li><strong class="date">Today</strong><a>Recycling</a></li>
  <li><strong class="date">Tomorrow</strong><a>Refuse</a></li>
  <li><strong class="date">Tue 3rd Nov</strong><a>Garden Waste</a></li>
</ul>
"""


@pytest.fixture
def council_page():
    """Mock council requests and freeze dates for deterministic collections."""
    with (
        patch(f"{MODULE_PATH}.requests.get") as get,
        patch(f"{MODULE_PATH}.datetime", wraps=datetime) as clock,
    ):
        get.return_value = Mock(text=COLLECTION_HTML)
        clock.today.return_value = datetime(2026, 10, 27)
        clock.now.return_value = datetime(2026, 10, 27)
        yield get


@pytest.mark.parametrize("uprn_kwargs", [{}, {"uprn": None}, {"uprn": ""}])
def test_legacy_property_url_without_separate_uprn(council_page, uprn_kwargs):
    """Use a property URL when the separate UPRN is absent or empty."""
    result = CharnwoodBoroughCouncil.CouncilClass().get_and_parse_data(
        PROPERTY_URL, skip_get_url=True, **uprn_kwargs
    )

    council_page.assert_called_once_with(PROPERTY_URL)
    assert result == {
        "bins": [
            {"type": "Recycling", "collectionDate": "27/10/2026"},
            {"type": "Refuse", "collectionDate": "28/10/2026"},
            {"type": "Garden Waste", "collectionDate": "03/11/2026"},
        ]
    }


@pytest.mark.parametrize("url", [None, "", PROPERTY_URL])
def test_explicit_uprn_takes_precedence_over_url(council_page, url):
    """Build the property URL from an explicit UPRN regardless of the URL."""
    result = CharnwoodBoroughCouncil.CouncilClass().parse_data(
        "", uprn="12345678902", url=url
    )

    council_page.assert_called_once_with(
        "https://my.charnwood.gov.uk/location?put=cbc12345678902"
        "&rememberme=0&redirect=%2F"
    )
    assert len(result["bins"]) == 3


@pytest.mark.parametrize("kwargs", [{}, {"uprn": None, "url": ""}, {"uprn": ""}])
def test_missing_uprn_and_url_fails_before_request(council_page, kwargs):
    """Reject missing identifiers without requesting an unscoped council page."""
    with pytest.raises(ValueError, match="Error getting identifier: Invalid UPRN"):
        CharnwoodBoroughCouncil.CouncilClass().parse_data("", **kwargs)

    council_page.assert_not_called()


@pytest.mark.parametrize("uprn_kwargs", [{}, {"uprn": None}, {"uprn": ""}])
@pytest.mark.parametrize(
    "url",
    [
        "https://my.charnwood.gov.uk/waste-calendar",
        "https://my.charnwood.gov.uk/location",
        "https://my.charnwood.gov.uk/location?put=",
        "https://my.charnwood.gov.uk/location?put=cbc",
        "https://my.charnwood.gov.uk/location?put=cbcnot-a-uprn",
        "https://my.charnwood.gov.uk/location?put=12345678901",
        "https://my.charnwood.gov.uk/waste-calendar?put=cbc12345678901",
        "https://example.com/location?put=cbc12345678901",
        "https://my.charnwood.gov.uk.example.com/location?put=cbc12345678901",
        "/location?put=cbc12345678901",
        "ftp://my.charnwood.gov.uk/location?put=cbc12345678901",
    ],
)
def test_invalid_property_url_fails_before_request(council_page, uprn_kwargs, url):
    """Reject general or invalid property URLs when no UPRN is configured."""
    with pytest.raises(ValueError, match="Error getting identifier: Invalid UPRN"):
        CharnwoodBoroughCouncil.CouncilClass().get_and_parse_data(
            url, skip_get_url=True, **uprn_kwargs
        )

    council_page.assert_not_called()


@pytest.mark.parametrize(
    "url, expected_url",
    [
        (
            "http://my.charnwood.gov.uk/location?put=cbc12345678901",
            "https://my.charnwood.gov.uk/location?put=cbc12345678901",
        ),
        (
            "http://my.charnwood.gov.uk/location?redirect=%2F&put=cbc12345678901",
            "https://my.charnwood.gov.uk/location?redirect=%2F&put=cbc12345678901",
        ),
        (
            "https://my.charnwood.gov.uk/location?redirect=%2F&put=cbc12345678901",
            "https://my.charnwood.gov.uk/location?redirect=%2F&put=cbc12345678901",
        ),
    ],
)
def test_property_url_variants_use_https(council_page, url, expected_url):
    """Upgrade legacy HTTP URLs while preserving property query parameters."""
    result = CharnwoodBoroughCouncil.CouncilClass().parse_data("", url=url)

    council_page.assert_called_once_with(expected_url)
    assert len(result["bins"]) == 3
