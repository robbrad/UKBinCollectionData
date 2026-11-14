"""Offline tests for Orkney's address search + bin lookup API (shapes from a live CI capture)."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import OrkneyIslandsCouncil

SEARCH = {
    "success": True,
    "addresses": [
        {"addressId": "134007618", "address": "1, INGALE, KIRKWALL, KW15 1UY"},
        {"addressId": "134007585", "address": "1, HORDALAND, KIRKWALL, KW15 1UN"},
    ],
}
# Dates are relative to today: the scraper drops past dates, so a fixed calendar
# silently turns these tests into "no collections" once it expires.
TODAY = date.today()


def _in(days: int) -> str:
    return (TODAY + timedelta(days=days)).isoformat()


def _dmy(days: int) -> str:
    return (TODAY + timedelta(days=days)).strftime("%d/%m/%Y")


LOOKUP = {
    "success": True,
    "binCollectionArea": {
        "area": "Area 3",
        "paper_and_metal": [
            {
                "date": _in(13),
                "summary": "Area 03 - Paper/thin card and metal cans",
            }
        ],
        "general_waste": [
            {"date": _in(-8), "summary": "Area 03 - Black/grey bins"},
            {"date": _in(6), "summary": "Area 03 - Black/grey bins"},
        ],
        "glass_and_plastic": [
            {"date": _in(27), "summary": "Area 03 - Glass and plastic"}
        ],
        "other": [],
    },
    "binConfig": {
        "paper_and_metal": {"label": "Paper & Metal"},
        "general_waste": {"label": "General Waste"},
        "glass_and_plastic": {"label": "Glass & Plastic"},
        "other": {"label": "Other"},
    },
}


def test_upcoming_collections_are_labelled_and_sorted():
    # The collection 8 days ago is dropped; the rest come back in date order.
    assert OrkneyIslandsCouncil._parse_collections(LOOKUP, TODAY) == {
        "bins": [
            {"type": "General Waste", "collectionDate": _dmy(6)},
            {"type": "Paper & Metal", "collectionDate": _dmy(13)},
            {"type": "Glass & Plastic", "collectionDate": _dmy(27)},
        ]
    }


def _session(*payloads):
    session = MagicMock()
    session.headers = {}
    session.get.side_effect = [
        MagicMock(json=MagicMock(return_value=p)) for p in payloads
    ]
    return session


def test_area_or_street_text_is_searched_and_first_address_looked_up():
    session = _session(SEARCH, LOOKUP)
    with patch.object(OrkneyIslandsCouncil.requests, "Session", return_value=session):
        data = OrkneyIslandsCouncil.CouncilClass().parse_data("", paon="Kirkwall")
    search, lookup = session.get.call_args_list
    assert search.kwargs["params"] == {"q": "Kirkwall"}
    assert lookup.kwargs["params"] == {"addressId": "134007618"}
    assert [b["collectionDate"] for b in data["bins"]] == [_dmy(6), _dmy(13), _dmy(27)]


def test_uprn_skips_the_search():
    session = _session(LOOKUP)
    with patch.object(OrkneyIslandsCouncil.requests, "Session", return_value=session):
        OrkneyIslandsCouncil.CouncilClass().parse_data("", uprn="134008211")
    assert session.get.call_count == 1
    assert session.get.call_args.kwargs["params"] == {"addressId": "134008211"}


def test_no_search_results_is_a_clear_error():
    session = _session({"success": True, "addresses": []})
    with patch.object(OrkneyIslandsCouncil.requests, "Session", return_value=session):
        with pytest.raises(ValueError, match="No Orkney address found for 'Nowhere'"):
            OrkneyIslandsCouncil.CouncilClass().parse_data("", paon="Nowhere")
