"""Unit tests for the Broxtowe Borough Council collection-table parser.

Broxtowe rebuilt this form on a new platform (confirmed live via CI's
own integration test against the real site, run across several rounds
to determine the new structure): the old
ctl00_ContentPlaceHolder1_FF5683* ASP.NET WebForms ids are gone,
replaced by semantic ids (FF5683-text/-find/-list), and the address
dropdown's option values are "U<uprn>|<full address text>". The
"Bin Details" section that follows address selection already contains
the results table directly - no extra step needed. The table's shape
(Bin Type / Collection Day / Last Collection / Next Collection, dates
formatted "%A, %d %B %Y") happens to match the old page's, so only the
table-parsing half is covered here; the Selenium navigation flow relies
on the live integration suite like the rest of this codebase's
Selenium-driven councils.
"""

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.councils.BroxtoweBoroughCouncil import (
    CouncilClass,
)

TABLE_HTML = """
<html>
  <body>
    <table>
      <tr>
        <th>Bin Type</th>
        <th>Collection Day</th>
        <th>Last Collection</th>
        <th>Next Collection</th>
      </tr>
      <tr>
        <td>GREEN 240L</td>
        <td>Friday</td>
        <td>Friday, 24 July 2026</td>
        <td>Friday, 07 August 2026</td>
      </tr>
      <tr>
        <td>GLASS BAG</td>
        <td>Friday</td>
        <td>Friday, 24 July 2026</td>
        <td>Friday, 21 August 2026</td>
      </tr>
      <tr>
        <td>BLACK 240L</td>
        <td>Friday</td>
        <td>Friday, 17 July 2026</td>
        <td>Friday, 31 July 2026</td>
      </tr>
    </table>
  </body>
</html>
"""


def test_parse_collection_table_extracts_next_collection_dates():
    soup = BeautifulSoup(TABLE_HTML, "html.parser")
    result = CouncilClass()._parse_collection_table(soup)

    assert result == {
        "bins": [
            {"type": "BLACK 240L", "collectionDate": "31/07/2026"},
            {"type": "GREEN 240L", "collectionDate": "07/08/2026"},
            {"type": "GLASS BAG", "collectionDate": "21/08/2026"},
        ]
    }


def test_parse_collection_table_skips_rows_with_no_date():
    html = TABLE_HTML.replace("<td>Friday, 31 July 2026</td>", "<td></td>", 1)
    soup = BeautifulSoup(html, "html.parser")
    result = CouncilClass()._parse_collection_table(soup)

    types = [b["type"] for b in result["bins"]]
    assert "BLACK 240L" not in types
    assert len(result["bins"]) == 2


def test_parse_collection_table_returns_empty_when_table_missing():
    soup = BeautifulSoup("<html><body>No table here</body></html>", "html.parser")
    result = CouncilClass()._parse_collection_table(soup)

    assert result == {"bins": []}
