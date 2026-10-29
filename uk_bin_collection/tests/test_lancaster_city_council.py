"""Unit tests for the Lancaster City Council scheduled-collections parser."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from uk_bin_collection.uk_bin_collection.councils.LancasterCityCouncil import (
    CouncilClass,
)

MODULE_PATH = "uk_bin_collection.uk_bin_collection.councils.LancasterCityCouncil"

HOME_HTML = '<a href="https://lcc-wrp.whitespacews.com/mop.php?serviceID=A&seq=1">Go</a>'
FORM_HTML = '<form action="https://lcc-wrp.whitespacews.com/mop.php?seq=2"></form>'
ADDRESS_HTML = '<a href="mop.php?serviceID=A&seq=3&pIndex=1">1 Test Street</a>'


def collection(date: str, service: str) -> str:
    return f"""
    <ul>
      <li><img src="img/{service}.png" alt="Collection Item" /></li>
      <li><p>{date}</p></li>
      <li><p>{service}</p></li>
    </ul>
    """


def schedule_html(*items: tuple[str, str]) -> str:
    body = "".join(collection(date, service) for date, service in items)
    return f'<section id="scheduled-collections">{body}</section>'


def parse_fixture(html: str):
    session = MagicMock()
    session.get.side_effect = [
        SimpleNamespace(text=HOME_HTML),
        SimpleNamespace(text=FORM_HTML),
        SimpleNamespace(text=html),
    ]
    session.post.return_value = SimpleNamespace(text=ADDRESS_HTML)
    with patch(f"{MODULE_PATH}.requests.Session", return_value=session):
        return CouncilClass().parse_data("", number="1", postcode="LA1 1RS")


def test_parse_data_keeps_recycling_streams_separate():
    result = parse_fixture(
        schedule_html(
            ("29/10/2026", "Domestic Waste Collection Service"),
            ("29/10/2026", "Food Waste Collection Service"),
            ("05/11/2026", "Recycling Red Collection Service"),
            ("12/11/2026", "Recycling Yellow Collection Service"),
        )
    )

    assert result == {
        "bins": [
            {"type": "Domestic Waste", "collectionDate": "29/10/2026"},
            {"type": "Food Waste", "collectionDate": "29/10/2026"},
            {"type": "Recycling Red", "collectionDate": "05/11/2026"},
            {"type": "Recycling Yellow", "collectionDate": "12/11/2026"},
        ]
    }


def test_parse_data_maps_unspecified_recycling_stream_to_recycling():
    result = parse_fixture(
        schedule_html(
            (
                "05/11/2026",
                "Recycling Collection - refer to calendar for stream",
            ),
        )
    )

    assert result == {
        "bins": [{"type": "Recycling", "collectionDate": "05/11/2026"}]
    }
