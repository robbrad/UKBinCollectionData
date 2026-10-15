"""Councils whose lookup succeeds but has no data should say so, not return []."""

from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import (
    SouthendOnSeaCityCouncil,
    TamworthBoroughCouncil,
)

LICHFIELD_NO_DATA = """
<main><aside class="alert alert--error"><h2 class="alert__heading">
We have no collection information for this property.</h2></aside></main>
"""

SOUTHEND_NO_DATA = {
    "WasteCollectionDates": {
        "UPRN": "100090632281",
        **{f"Container{i}CollectionDetails": None for i in range(1, 12)},
    }
}


def test_tamworth_unknown_property_is_a_clear_error():
    with patch.object(
        TamworthBoroughCouncil.requests,
        "get",
        return_value=MagicMock(text=LICHFIELD_NO_DATA),
    ):
        with pytest.raises(
            ValueError, match="no collection information for UPRN 100031767448"
        ):
            TamworthBoroughCouncil.CouncilClass().parse_data("", uprn="100031767448")


def test_southend_all_empty_containers_is_a_clear_error():
    response = MagicMock(status_code=200)
    response.json.return_value = SOUTHEND_NO_DATA
    with patch.object(SouthendOnSeaCityCouncil.requests, "get", return_value=response):
        with pytest.raises(ValueError, match="no containers for UPRN 100090632281"):
            SouthendOnSeaCityCouncil.CouncilClass().parse_data("", uprn="100090632281")


def test_southend_still_parses_real_collections():
    data = {
        "WasteCollectionDates": {
            "Container1CollectionDetails": {
                "ContainerDescription": "Refuse Bin",
                "CollectionDate": "2026-10-20T00:00:00",
            }
        }
    }
    response = MagicMock(status_code=200)
    response.json.return_value = data
    with patch.object(SouthendOnSeaCityCouncil.requests, "get", return_value=response):
        result = SouthendOnSeaCityCouncil.CouncilClass().parse_data(
            "", uprn="100090632281"
        )
    assert result == {"bins": [{"type": "Refuse Bin", "collectionDate": "20/10/2026"}]}


LICHFIELD_DATES = """
<h3 class="bin-collection-tasks__heading">Your next household waste collection</h3>
<p class="bin-collection-tasks__date">20th October</p>
<h3 class="bin-collection-tasks__heading">Your next blue bin collection</h3>
<p class="bin-collection-tasks__date">27th October</p>
"""


def test_tamworth_parses_collection_tasks():
    with patch.object(
        TamworthBoroughCouncil.requests,
        "get",
        return_value=MagicMock(text=LICHFIELD_DATES),
    ):
        data = TamworthBoroughCouncil.CouncilClass().parse_data("", uprn="100031767448")
    assert [b["type"] for b in data["bins"]] == ["household waste", "blue bin"]
    assert all(
        b["collectionDate"].startswith(("20/10/", "27/10/")) for b in data["bins"]
    )
