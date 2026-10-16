"""Unit tests for the Swansea recycling search scraper.

Swansea's site can answer a search with the previous search's result
(another postcode's address and dates), so the scraper must check the
result's address is in the postcode it asked for, and retry once.
"""

from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import SwanseaCouncil
from uk_bin_collection.uk_bin_collection.councils.SwanseaCouncil import CouncilClass

FORM = '<form><input type="hidden" name="__VIEWSTATE" value="vs"></form>'


def result_page(address, refuse="Monday 05/10/2026", recycling="Monday 12/10/2026"):
    return (
        f"<p>Address: {address}</p><p>Collection Day: Monday</p>"
        f'<span id="lblNextRefuse">{refuse}</span>'
        f'<span id="lblNextRecycling">{recycling}</span>'
    )


def run(*pages, postcode="SA4 3PQ"):
    """Run the scraper with each search answered by the next of pages."""
    sessions = []
    for page in pages:
        session = MagicMock()
        session.get.return_value = MagicMock(text=FORM)
        session.post.return_value = MagicMock(text=page)
        sessions.append(session)
    with patch.object(
        SwanseaCouncil.requests, "Session", side_effect=sessions
    ), patch.object(SwanseaCouncil.time, "sleep"):
        return (
            CouncilClass().parse_data("", postcode=postcode, uprn="100100324821"),
            sessions,
        )


def test_searches_by_postcode_only():
    data, [session] = run(result_page("ORCHARD DRIVE, THREE CROSSES, SA4 3PQ"))
    assert data["bins"] == [
        {"type": "Pink Week", "collectionDate": "05/10/2026"},
        {"type": "Green Week", "collectionDate": "12/10/2026"},
    ]
    sent = session.post.call_args.kwargs["data"]
    assert (
        sent["txtPostCode"] == "SA4 3PQ"
        and sent["txtRoadName"] == ""
        and sent["__VIEWSTATE"] == "vs"
    )


def test_never_returns_another_postcodes_result():
    another = result_page("ORCHARD DRIVE, THREE CROSSES, SA4 3PQ")
    with pytest.raises(ValueError, match="No collection data found"):
        run(another, another, postcode="SA1 3SN")


def test_retries_once_after_a_stale_result():
    data, sessions = run(
        result_page("ORCHARD DRIVE, THREE CROSSES, SA4 3PQ"),
        result_page("SOME STREET, SWANSEA, SA1 3SN"),
        postcode="SA1 3SN",
    )
    assert len(sessions) == 2 and len(data["bins"]) == 2
