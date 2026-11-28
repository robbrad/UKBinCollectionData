"""Offline tests for East Lindsey's address matching and results parsing.

The council's iCM form is driven over plain HTTP (curl_cffi), since automated
Chrome is served a Cloudflare challenge on the form POST.
"""

import base64
import json

import pytest

from uk_bin_collection.uk_bin_collection.councils.EastLindseyDistrictCouncil import (
    encode_submitted_variables,
    parse_results,
    select_address,
)


def _address(line1: str, uprn: str) -> dict:
    return {
        "uprn": uprn,
        "line1": line1,
        "line2": "",
        "line4": "Sibsey",
        "town": "BOSTON",
        "county": "Lincolnshire",
        "postcode": "PE22 0YD",
        "source": "NLPGEL",
    }


ADDRESSES = [
    _address("1 Harvester Way", "100"),
    _address("11 Harvester Way", "101"),
    _address("1A Harvester Way", "102"),
    _address("Rose Cottage", "103"),
]


def _results_page(result: dict) -> str:
    blob = base64.b64encode(json.dumps({"result": [result]}).encode()).decode()
    return f"var X_FIELD12Data = JSON.parse(helper.utilDecode('{blob}'));"


def test_select_address_is_start_anchored_and_whole_word():
    assert select_address(ADDRESSES, "1")["uprn"] == "100"
    assert select_address(ADDRESSES, "11")["uprn"] == "101"
    assert select_address(ADDRESSES, "rose cottage")["uprn"] == "103"


def test_select_address_raises_on_zero_or_multiple():
    with pytest.raises(ValueError, match="found 0"):
        select_address(ADDRESSES, "5")
    with pytest.raises(ValueError, match="found 2"):
        select_address([ADDRESSES[0], _address("1 Other Close", "9")], "1")


def test_encode_submitted_variables_carries_uprn_and_source():
    decoded = json.loads(base64.b64decode(encode_submitted_variables(ADDRESSES[0])))
    assert decoded["ADDRESSUPRN"] == {"value": "100", "scope": "SERVERCLIENTWITHUPDATE"}
    assert decoded["ADDRESSSOURCE"]["value"] == "NLPGEL"


def test_parse_results_maps_each_bin_and_sorts():
    page = _results_page(
        {
            "wastenextref": "Thursday 10th December 2026",
            "wastenextrec": "Thursday 3rd December 2026",
            "wastenextpur": "Thursday 17th December 2026",
            "wastenextfood": None,
            "greenday": "Thursday",
        }
    )
    assert parse_results(page) == {
        "bins": [
            {"type": "Recycling (Grey Bin)", "collectionDate": "03/12/2026"},
            {"type": "Refuse (Black Bin)", "collectionDate": "10/12/2026"},
            {"type": "Paper (Purple-Lidded Bin)", "collectionDate": "17/12/2026"},
        ]
    }


def test_parse_results_reports_out_of_area():
    with pytest.raises(ValueError, match="out of its area"):
        parse_results("<h3>Address Out Of Area</h3>")


def test_parse_results_raises_when_no_dates():
    with pytest.raises(ValueError):
        parse_results(_results_page({"wasteuprn": "1"}))
