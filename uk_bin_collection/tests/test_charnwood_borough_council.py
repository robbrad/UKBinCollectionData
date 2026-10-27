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
    with pytest.raises(ValueError, match="Error getting identifier: Invalid UPRN"):
        CharnwoodBoroughCouncil.CouncilClass().parse_data("", **kwargs)

    council_page.assert_not_called()
