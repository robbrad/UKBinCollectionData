"""East Herts reads bin days from an AchieveForms lookup; these pin that flow."""

from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import EastHertsCouncil

MODULE_PATH = "uk_bin_collection.uk_bin_collection.councils.EastHertsCouncil"
TEST_UPRN = "10023088183"


def _session_answering(lookup_body):
    session = MagicMock()
    session.get.return_value.json.return_value = {"auth-session": "test-sid"}
    session.post.return_value.json.return_value = lookup_body
    return session


def _run_with(lookup_body):
    session = _session_answering(lookup_body)
    with patch(f"{MODULE_PATH}.requests.session", return_value=session):
        result = EastHertsCouncil.CouncilClass().parse_data("", uprn=TEST_UPRN)
    return result, session


def _lookup_returning(rows):
    return {"integration": {"transformed": {"rows_data": {"0": rows}}}}


# Shaped like the council's live answer on 2026-11-06, including the
# whitespace it now wraps around each service name.
LIVE_ROWS = {
    "RecyclingServiceName": "\n                Mixed Recycling (Black)\n            ",
    "RecyclingNextDate": "Tuesday 17th November",
    "RecyclingImageURL": "",
    "RefuseServiceName": "\n                Refuse (Purple)\n            ",
    "RefuseNextDate": "Tuesday 10th November",
    "RefuseImageURL": "",
}


def test_it_queries_the_lookup_the_council_form_uses_now():
    _, session = _run_with(_lookup_returning(LIVE_ROWS))

    params = session.post.call_args.kwargs["params"]
    assert params["id"] == "6accfd6441228"


def test_a_council_error_body_is_reported_with_the_councils_message():
    with pytest.raises(ValueError, match="User Package  Not Found"):
        _run_with({"error": "User Package  Not Found"})


def test_service_names_are_returned_without_surrounding_whitespace():
    result, _ = _run_with(_lookup_returning(LIVE_ROWS))

    assert {bin_["type"] for bin_ in result["bins"]} == {
        "Mixed Recycling (Black)",
        "Refuse (Purple)",
    }


def test_bins_are_sorted_by_collection_date():
    result, _ = _run_with(_lookup_returning(LIVE_ROWS))

    assert [bin_["type"] for bin_ in result["bins"]] == [
        "Refuse (Purple)",
        "Mixed Recycling (Black)",
    ]
