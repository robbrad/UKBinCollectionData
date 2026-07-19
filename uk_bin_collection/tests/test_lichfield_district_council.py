"""Unit tests for the Lichfield District Council collection-card parser."""

from datetime import datetime as real_datetime
from types import SimpleNamespace
from unittest.mock import patch

from uk_bin_collection.uk_bin_collection.councils.LichfieldDistrictCouncil import (
    CouncilClass,
)

MODULE_PATH = "uk_bin_collection.uk_bin_collection.councils.LichfieldDistrictCouncil"

RESULTS_HTML = """
<html>
  <body>
    <ul class="list bin-collection-tasks">
      <li class="list__item">
        <h3 class="bin-collection-tasks__heading">
          <span class="visually-hidden">Your next </span>Food Waste Caddy
          <span class="visually-hidden"> collection</span>
        </h3>
        <p class="bin-collection-tasks__frequency">
          Collected every <strong>Thursday</strong>
        </p>
      </li>
      <li class="list__item">
        <h3 class="bin-collection-tasks__heading">
          <span class="visually-hidden">Your next </span>Brown Bin
          <span class="visually-hidden"> collection</span>
        </h3>
        <p class="bin-collection-tasks__date">23rd July</p>
      </li>
      <li class="list__item">
        <h3 class="bin-collection-tasks__heading">
          <span class="visually-hidden">Your next </span>Blue Bin
          <span class="visually-hidden"> collection</span>
        </h3>
        <p class="bin-collection-tasks__date">23rd July</p>
      </li>
      <li class="list__item">
        <h3 class="bin-collection-tasks__heading">
          <span class="visually-hidden">Your next </span>Black Bin
          <span class="visually-hidden"> collection</span>
        </h3>
        <p class="bin-collection-tasks__date">30th July</p>
      </li>
      <li class="list__item">
        <h3 class="bin-collection-tasks__heading">
          <span class="visually-hidden">Your next </span>Purple Bin
          <span class="visually-hidden"> collection</span>
        </h3>
        <p class="bin-collection-tasks__date">6th August</p>
      </li>
      <li class="list__item">
        <h3 class="bin-collection-tasks__heading">
          Download <span class="visually-hidden">your bin </span>collection calendar
        </h3>
      </li>
    </ul>
  </body>
</html>
"""


def parse_fixture(html: str, now: real_datetime):
    response = SimpleNamespace(text=html)
    with patch(f"{MODULE_PATH}.requests.get", return_value=response), patch(
        f"{MODULE_PATH}.datetime"
    ) as mock_datetime:
        mock_datetime.now.return_value = now
        mock_datetime.strptime.side_effect = real_datetime.strptime
        return CouncilClass().parse_data("", uprn="100031694085")


def test_parse_data_keeps_collection_dates_with_their_own_cards():
    result = parse_fixture(RESULTS_HTML, real_datetime(2026, 7, 19, 10, 0))

    assert result == {
        "bins": [
            {"type": "Food Waste", "collectionDate": "23/07/2026"},
            {"type": "Brown Bin", "collectionDate": "23/07/2026"},
            {"type": "Blue Bin", "collectionDate": "23/07/2026"},
            {"type": "Black Bin", "collectionDate": "30/07/2026"},
            {"type": "Purple Bin", "collectionDate": "06/08/2026"},
        ]
    }


def test_parse_data_rolls_explicit_dates_into_the_next_year():
    html = RESULTS_HTML.replace("23rd July", "5th March")
    result = parse_fixture(html, real_datetime(2026, 12, 20, 10, 0))

    assert result["bins"][1]["collectionDate"] == "05/03/2027"
    assert result["bins"][2]["collectionDate"] == "05/03/2027"
