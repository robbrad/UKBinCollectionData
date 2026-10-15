"""Offline tests for the shared SocietyWorks/FixMyStreet scraper (Sutton, Bromley, ...)."""

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from uk_bin_collection.uk_bin_collection.councils.LondonBoroughSutton import (
    CouncilClass,
)
from uk_bin_collection.uk_bin_collection.councils.SocietyWorks import (
    SocietyWorksClass,
)

BASE = "https://waste-services.sutton.gov.uk/"


def response(status=200, text="", headers=None, content=None):
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    resp.content = content if content is not None else text.encode()
    resp.headers = headers or {}
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp


def ics(*events):
    body = "".join(
        "BEGIN:VEVENT\r\n"
        f"UID:{i}@example\r\n"
        f"DTSTART;VALUE=DATE:{day.strftime('%Y%m%d')}\r\n"
        f"SUMMARY:{summary}\r\n"
        "END:VEVENT\r\n"
        for i, (summary, day) in enumerate(events)
    )
    return f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:test\r\n{body}END:VCALENDAR\r\n"


def council_with(get=None, post=None):
    council = CouncilClass()
    council.session = MagicMock()
    council.session.get.side_effect = get
    council.session.post.side_effect = post
    return council


SOON = date.today() + timedelta(days=3)
LATER = date.today() + timedelta(days=10)
CALENDAR = ics(("Non-recyclable waste", LATER), ("Food waste", SOON))


def calendar_for(property_id):
    def get(url, **kwargs):
        if url == f"{BASE}waste/{property_id}/calendar.ics":
            return response(text=CALENDAR)
        raise AssertionError(f"unexpected GET {url}")

    return get


def test_session_sends_the_non_browser_user_agent():
    # A full browser UA gets 503s from these sites since Oct 2026 (#2255).
    assert CouncilClass().session.headers["User-Agent"] == SocietyWorksClass.USER_AGENT
    assert "Mozilla" not in SocietyWorksClass.USER_AGENT


def test_property_id_in_configured_url_is_used_directly():
    council = council_with(get=calendar_for("6087017"))
    data = council.parse_data("", url=f"{BASE}waste/6087017")
    assert data["bins"] == [
        {"type": "Food waste", "collectionDate": SOON.strftime("%d/%m/%Y")},
        {"type": "Non-recyclable waste", "collectionDate": LATER.strftime("%d/%m/%Y")},
    ]


def test_uprn_is_resolved_through_the_property_redirect():
    def get(url, **kwargs):
        if url == f"{BASE}property/4473006":
            return response(302, headers={"Location": "/waste/123456"})
        return calendar_for("123456")(url)

    data = council_with(get=get).parse_data("", url=BASE, uprn="4473006")
    assert len(data["bins"]) == 2


def test_unknown_uprn_is_treated_as_a_property_id():
    def get(url, **kwargs):
        if url == f"{BASE}property/999":
            return response(404)
        return calendar_for("999")(url)

    assert len(council_with(get=get).parse_data("", url=BASE, uprn="999")["bins"]) == 2


def test_redirect_without_location_is_an_error():
    council = council_with(get=lambda url, **kw: response(200))
    with pytest.raises(ValueError, match="Location header"):
        council.parse_data("", url=BASE, uprn="4473006")


def test_non_numeric_uprn_is_rejected():
    with pytest.raises(ValueError, match="Invalid UPRN"):
        council_with().parse_data("", url=BASE, uprn="abc")


ADDRESS_PAGE = """
<select id="address">
  <option value="">Pick an address</option>
  <option value="111">56 Greyhound Road, Sutton, SM1 4BJ</option>
  <option value="222">6 Greyhound Road, Sutton, SM1 4BJ</option>
</select>
"""


def test_house_number_matches_the_start_of_the_address_only():
    council = council_with(
        get=calendar_for("222"), post=lambda url, **kw: response(text=ADDRESS_PAGE)
    )
    data = council.parse_data("", url=BASE, postcode="SM1 4BJ", paon="6")
    assert len(data["bins"]) == 2
    council.session.post.assert_called_once()
    assert council.session.post.call_args.kwargs["data"] == {"postcode": "SM1 4BJ"}


@pytest.mark.parametrize(
    "page",
    [ADDRESS_PAGE, "<p>No addresses found</p>"],
    ids=["no-matching-house", "no-address-list"],
)
def test_unresolvable_address_is_an_error(page):
    council = council_with(post=lambda url, **kw: response(text=page))
    with pytest.raises(ValueError, match="Could not resolve property"):
        council.parse_data("", url=BASE, postcode="SM1 4BJ", paon="99")


def test_non_calendar_response_is_an_error():
    council = council_with(get=lambda url, **kw: response(text="<html>Error</html>"))
    with pytest.raises(ValueError, match="invalid data"):
        council.parse_data("", url=f"{BASE}waste/6087017")
