"""Unit tests for the Mid Suffolk District Council collection-table parser."""

import pytest
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.councils.MidSuffolkDistrictCouncil import (
    CouncilClass,
)

TABLE_HTML = """
<html>
  <body>
    <table class="table">
      <tbody>
        <tr>
          <td>Refuse</td>
          <td>Monday 04 Aug 2026</td>
          <td>Fortnightly</td>
          <td>Monday 18 Aug 2026</td>
        </tr>
        <tr>
          <td>Recycling</td>
          <td>Monday 11 Aug 2026</td>
          <td>Fortnightly</td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


def test_parse_collection_table_includes_following_collection_date():
    soup = BeautifulSoup(TABLE_HTML, "html.parser")
    result = CouncilClass()._parse_collection_table(soup)

    assert result == {
        "bins": [
            {"type": "Refuse", "collectionDate": "04/08/2026"},
            {"type": "Refuse", "collectionDate": "18/08/2026"},
            {"type": "Recycling", "collectionDate": "11/08/2026"},
        ]
    }


def test_parse_collection_table_ignores_rows_with_no_next_date():
    html = TABLE_HTML.replace(
        "<td>Recycling</td>\n          <td>Monday 11 Aug 2026</td>",
        "<td>Recycling</td>\n          <td></td>",
    )
    soup = BeautifulSoup(html, "html.parser")
    result = CouncilClass()._parse_collection_table(soup)

    assert result == {
        "bins": [
            {"type": "Refuse", "collectionDate": "04/08/2026"},
            {"type": "Refuse", "collectionDate": "18/08/2026"},
        ]
    }


def test_parse_collection_table_returns_empty_when_table_missing():
    soup = BeautifulSoup("<html><body>No table here</body></html>", "html.parser")
    result = CouncilClass()._parse_collection_table(soup)

    assert result == {"bins": []}


def test_parse_collection_table_raises_on_malformed_date():
    # A non-empty but unparseable date is format drift, not a missing
    # value - it should surface loudly rather than being dropped silently.
    html = TABLE_HTML.replace("Monday 04 Aug 2026", "Not A Real Date")
    soup = BeautifulSoup(html, "html.parser")

    with pytest.raises(ValueError):
        CouncilClass()._parse_collection_table(soup)
