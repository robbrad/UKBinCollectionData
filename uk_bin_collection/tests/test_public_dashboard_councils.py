"""Offline tests for the "Public Dashboard" platform (Slough, Portsmouth)."""

import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import (
    HighPeakCouncil,
    PortsmouthCityCouncil,
    SloughBoroughCouncil,
    StaffordshireMoorlandsDistrictCouncil,
)

TOKEN = '<input name="__RequestVerificationToken" type="hidden" value="tok">'
PREMISES = [
    {"UPRN": 1775027503.0, "Premises": "1 EXAMPLE ROAD"},
    {"UPRN": 1775027504.0, "Premises": "2 EXAMPLE ROAD"},
]
FUTURE = date.today() + timedelta(days=5)
PAST = date.today() - timedelta(days=5)
EVENTS = [
    {"Subject": "RECYCLING", "StartTime": f"{FUTURE}T00:00:00"},
    {"Subject": "REFUSE", "StartTime": f"{PAST}T00:00:00"},
]


def page(body=""):
    return MagicMock(text=f"<html><body>{TOKEN}{body}</body></html>")


def run(council_module, **kwargs):
    session = MagicMock()
    session.get.return_value = page()
    session.post.side_effect = [
        page(
            f"<script>ejs.data.DataUtil.parse.isJson({json.dumps(PREMISES)})</script>"
        ),
        page(
            "<script>var eventSettings = {dataSource: "
            f"ejs.data.DataUtil.parse.isJson({json.dumps(EVENTS)})}}</script>"
        ),
    ]
    with patch.object(
        SloughBoroughCouncil.requests, "Session", return_value=session
    ), patch.object(SloughBoroughCouncil, "check_postcode", return_value=True):
        data = council_module.CouncilClass().parse_data(
            "", postcode="PO4 0LE", **kwargs
        )
    return data, session


@pytest.mark.parametrize(
    "module, base",
    [
        (
            PortsmouthCityCouncil,
            "https://recyclingandrubbish.portsmouth.gov.uk/PublicDashboard",
        ),
        (SloughBoroughCouncil, "https://waste.slough.gov.uk/PublicDashboard"),
        (HighPeakCouncil, "https://bins.highpeak.gov.uk/PublicDashboard"),
        (
            StaffordshireMoorlandsDistrictCouncil,
            "https://bins.staffsmoorlands.gov.uk/PublicDashboard",
        ),
    ],
    ids=["portsmouth", "slough", "high-peak", "staffs-moorlands"],
)
def test_each_council_uses_its_own_dashboard(module, base):
    _, session = run(module, uprn="1775027504")
    assert session.get.call_args.args[0] == base
    assert [c.args[0] for c in session.post.call_args_list] == [
        f"{base}?handler=SearchPostcode",
        f"{base}?handler=SelectPrem",
    ]


def test_uprn_selects_the_premises_and_past_dates_are_dropped():
    data, session = run(PortsmouthCityCouncil, uprn="1775027504")
    assert (
        session.post.call_args_list[1].kwargs["data"]["SelectedPremises"]
        == "1775027504"
    )
    assert data == {
        "bins": [{"type": "Recycling", "collectionDate": FUTURE.strftime("%d/%m/%Y")}]
    }


@pytest.mark.parametrize(
    "paon, expected",
    [
        ("2", "1775027504"),
        ("2 Example Road", "1775027504"),
        ("2, Example Road", "1775027504"),
    ],
    ids=["number", "number-and-street", "punctuation-ignored"],
)
def test_house_number_matching(paon, expected):
    _, session = run(HighPeakCouncil, paon=paon)
    assert session.post.call_args_list[1].kwargs["data"]["SelectedPremises"] == expected
