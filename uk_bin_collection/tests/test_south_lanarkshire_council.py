"""Unit tests for the South Lanarkshire Council XFP-form scraper.

The council retired the static "directory_record" bin-day page this
scraper used to parse (#2231) in favour of an interactive form:
postcode -> address dropdown -> collection schedule. These tests mock
the three HTTP round trips with fixtures modelled on the live form's
actual markup (captured via a live CI run), so the table-parsing logic
is verified without a network call.
"""

from types import SimpleNamespace
from unittest.mock import patch

from uk_bin_collection.uk_bin_collection.councils.SouthLanarkshireCouncil import (
    CouncilClass,
)

FORM_PAGE = """
<html><body>
<form>
<input type="hidden" name="__token" value="tok1">
<input type="hidden" name="page" value="12">
<input type="text" name="q123_0_0">
</form>
</body></html>
"""

ADDRESS_DROPDOWN_PAGE = """
<html><body>
<input type="hidden" name="__token" value="tok2">
<select name="q123_1_0">
<option value="484186511">11 Philipshill Road, East Kilbride, Glasgow, G74 5DQ</option>
<option value="484186512">15 Philipshill Road, East Kilbride, Glasgow, G74 5DQ</option>
<option value="111111">I cannot find my property</option>
</select>
</body></html>
"""

BIN_TABLE_PAGE = """
<html><body>
<table id="bin-table">
<tbody>
<tr><th>Bin colour</th><th>Type of bin</th><th>Collection day and date</th></tr>
<tr>
<td><h4 class="imageCaption"><img alt="Black bin" src="/images/bin_black.png"/></h4></td>
<td><p><a href="/info/1841" title="Black/green bin - non-recyclable waste">Black/green bin - non-recyclable waste</a></p></td>
<td><h4>05/10/2026</h4></td>
</tr>
<tr>
<td><h4 class="imageCaption"><img alt="Blue bin" src="/images/bin_blue.png"/></h4></td>
<td><p><a href="/info/1841/2" title="Blue bin">Blue bin - paper and card recycling</a></p></td>
<td><h4>28/09/2026</h4></td>
</tr>
</tbody>
</table>
</body></html>
"""

NO_DROPDOWN_PAGE = "<html><body><p>No addresses found</p></body></html>"


def _resp(text):
    return SimpleNamespace(text=text)


def _valid_postcode_check():
    return patch("requests.get", return_value=SimpleNamespace(status_code=200))


def test_parses_the_bin_table_into_sorted_bins():
    with _valid_postcode_check(), patch(
        "requests.Session.get", return_value=_resp(FORM_PAGE)
    ), patch(
        "requests.Session.post",
        side_effect=[_resp(ADDRESS_DROPDOWN_PAGE), _resp(BIN_TABLE_PAGE)],
    ):
        result = CouncilClass().parse_data("", postcode="G74 5DQ")

    assert result == {
        "bins": [
            {
                "type": "Blue bin - paper and card recycling",
                "collectionDate": "28/09/2026",
            },
            {
                "type": "Black/green bin - non-recyclable waste",
                "collectionDate": "05/10/2026",
            },
        ]
    }


def test_matches_a_specific_address_by_house_number():
    with _valid_postcode_check(), patch(
        "requests.Session.get", return_value=_resp(FORM_PAGE)
    ), patch(
        "requests.Session.post",
        side_effect=[_resp(ADDRESS_DROPDOWN_PAGE), _resp(BIN_TABLE_PAGE)],
    ) as mock_post:
        CouncilClass().parse_data("", postcode="G74 5DQ", paon="15")

    final_call_data = mock_post.call_args_list[1].kwargs["data"]
    assert final_call_data["q123_1_0"] == "484186512"


def test_raises_a_clear_error_when_house_number_not_found():
    with _valid_postcode_check(), patch(
        "requests.Session.get", return_value=_resp(FORM_PAGE)
    ), patch("requests.Session.post", return_value=_resp(ADDRESS_DROPDOWN_PAGE)):
        try:
            CouncilClass().parse_data("", postcode="G74 5DQ", paon="999")
            assert False, "expected a ValueError"
        except ValueError as exc:
            assert "999" in str(exc)


def test_raises_a_clear_error_when_no_addresses_found():
    with _valid_postcode_check(), patch(
        "requests.Session.get", return_value=_resp(FORM_PAGE)
    ), patch("requests.Session.post", return_value=_resp(NO_DROPDOWN_PAGE)):
        try:
            CouncilClass().parse_data("", postcode="G74 5DQ")
            assert False, "expected a ValueError"
        except ValueError as exc:
            assert "G74 5DQ" in str(exc)
