"""Epping Forest's anonymous AchieveService lookup and optional services."""

from datetime import datetime as real_datetime
from unittest.mock import patch

import pytest
import requests

from uk_bin_collection.uk_bin_collection.councils import (
    EppingForestDistrictCouncil as council,
)

MODULE = council.__name__
PUBLIC_SCHOOL_UPRN = "100091624148"


@pytest.fixture(autouse=True)
def fixed_today():
    with patch(f"{MODULE}.datetime", wraps=real_datetime) as clock:
        clock.now.return_value = real_datetime(2026, 11, 17)
        yield


def payload(**fields):
    return {
        "status": "done",
        "integration": {"transformed": {"rows_data": {"0": fields}}},
    }


def test_four_separate_services_keep_existing_names_and_correct_dates():
    result = council.parse_response(
        payload(
            GeneralWasteServiceNextCollection="2026-11-17T00:00:00",
            RecyclingServiceNextCollection="2026-11-24T00:00:00",
            FoodWasteServiceNextCollection="2026-11-17T00:00:00",
            FoodWasteServiceItem="BATTERIES",
            GardenWasteServiceNextCollection="2026-11-24T00:00:00",
            GardenWasteServiceTo="2027-03-31T23:59:59",
        )
    )
    assert result == {
        "bins": [
            {"type": "Black Bin", "collectionDate": "17/11/2026"},
            {"type": "Food Waste Bin", "collectionDate": "17/11/2026"},
            {"type": "Blue Box and Recycling Sack", "collectionDate": "24/11/2026"},
            {"type": "Green-lidded Bin", "collectionDate": "24/11/2026"},
        ]
    }


def test_properties_without_all_services_are_supported():
    # The public school fixture has food and recycling but no refuse or garden.
    assert council.parse_response(
        payload(
            FoodWasteServiceNextCollection="2026-11-20T00:00:00",
            RecyclingServiceNextCollection="2026-11-27T00:00:00",
            FoodGardenServiceNextCollection="",
            GardenWasteServiceNextCollection="0001-01-01T00:00:00",
        )
    ) == {
        "bins": [
            {"type": "Food Waste Bin", "collectionDate": "20/11/2026"},
            {"type": "Blue Box and Recycling Sack", "collectionDate": "27/11/2026"},
        ]
    }


@pytest.mark.parametrize(
    "response",
    [
        {"status": "error"},
        {"status": "done", "error": "lookup failed"},
        {"status": "done"},
        payload(),
    ],
)
def test_failed_or_empty_lookup_is_not_a_success(response):
    with pytest.raises(ValueError, match="Epping Forest"):
        council.parse_response(response)


def test_stale_dates_are_not_published():
    with pytest.raises(ValueError, match="past Black Bin"):
        council.parse_response(
            payload(GeneralWasteServiceNextCollection="2024-10-22T00:00:00")
        )


def test_lookup_uses_same_anonymous_session_and_uprn():
    with patch(f"{MODULE}.requests.Session") as session_class:
        session = session_class.return_value.__enter__.return_value
        session.get.return_value.json.return_value = {
            "auth-session": "anonymous-session"
        }
        session.post.return_value.json.return_value = payload(
            FoodWasteServiceNextCollection="2026-11-20T00:00:00"
        )
        result = council.CouncilClass().parse_data("", uprn=PUBLIC_SCHOOL_UPRN)
        assert result["bins"][0]["collectionDate"] == "20/11/2026"
        session.get.return_value.raise_for_status.assert_called_once()
        session.post.return_value.raise_for_status.assert_called_once()
        session.post.assert_called_once_with(
            f"{council.BASE_URL}/apibroker/runLookup",
            params={"id": "6651dfb99a74d", "sid": "anonymous-session"},
            json={
                "formValues": {
                    "Section 1": {"LookupUPRN": {"value": PUBLIC_SCHOOL_UPRN}}
                }
            },
            timeout=30,
        )


@pytest.mark.parametrize("uprn", [None, "", "not-a-uprn", "1" * 13])
def test_uprn_is_required_before_network_access(uprn):
    with patch(f"{MODULE}.requests.Session") as session_class:
        with pytest.raises(ValueError, match="UPRN"):
            council.CouncilClass().parse_data("", uprn=uprn)
        session_class.assert_not_called()


def test_session_and_http_failures_are_reported():
    with patch(f"{MODULE}.requests.Session") as session_class:
        session = session_class.return_value.__enter__.return_value
        session.get.return_value.json.return_value = {}
        with pytest.raises(ValueError, match="lookup session"):
            council.CouncilClass().parse_data("", uprn=PUBLIC_SCHOOL_UPRN)
        session.post.assert_not_called()
        session.get.return_value.raise_for_status.side_effect = requests.HTTPError(
            "503"
        )
        with pytest.raises(requests.HTTPError):
            council.CouncilClass().parse_data("", uprn=PUBLIC_SCHOOL_UPRN)
