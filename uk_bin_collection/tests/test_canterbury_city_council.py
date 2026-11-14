"""Offline tests for Canterbury's bin-dates API (shapes from the council's own widget)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import CanterburyCityCouncil

DATES = {
    "blackBinDay": ["2026-11-24T00:00:00", "2026-12-08T00:00:00"],
    "recyclingBinDay": ["2026-11-17T00:00:00"],
    "redRecyclingBinDay": [],
    "blueRecyclingBinDay": None,
    "foodBinDay": ["2026-11-17T00:00:00"],
    "gardenBinDay": ["2026-11-30T00:00:00"],
}


def _response(status=200, dates=DATES):
    response = MagicMock(status_code=status)
    response.json.return_value = {"dates": dates}
    response.raise_for_status.side_effect = (
        None if status < 400 else Exception(f"HTTP {status}")
    )
    return response


def _run(response, uprn="10000000001"):
    with patch.object(
        CanterburyCityCouncil.requests, "post", return_value=response
    ) as post:
        data = CanterburyCityCouncil.CouncilClass().parse_data("", uprn=uprn)
    return data, post


def test_object_shaped_dates_are_labelled_and_sorted():
    data, post = _run(_response())
    assert data["bins"] == [
        {"type": "Recycling", "collectionDate": "17/11/2026"},
        {"type": "Food", "collectionDate": "17/11/2026"},
        {"type": "General", "collectionDate": "24/11/2026"},
        {"type": "Garden", "collectionDate": "30/11/2026"},
        {"type": "General", "collectionDate": "08/12/2026"},
    ]
    assert post.call_args.kwargs["json"] == {"uprn": "10000000001", "usrn": "1"}
    assert post.call_args.kwargs["timeout"] == 30


def test_the_older_json_string_shape_still_parses():
    data, _ = _run(_response(dates=json.dumps(DATES)))
    assert len(data["bins"]) == 5


def test_a_403_is_reported_as_a_block_not_a_bad_uprn():
    with pytest.raises(ConnectionError, match="403 Forbidden.*not a bad UPRN"):
        _run(_response(status=403))


@pytest.mark.parametrize("dates", [None, {}, {"blackBinDay": [], "foodBinDay": None}])
def test_no_collections_is_an_error_not_an_empty_result(dates):
    with pytest.raises(ValueError, match="No collection"):
        _run(_response(dates=dates))
