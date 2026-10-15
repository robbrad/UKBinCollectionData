"""Regression tests for Doncaster's OnCreate collection calendar."""

import html
import json
from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import TimeoutException

from uk_bin_collection.uk_bin_collection.councils.DoncasterCouncil import CouncilClass

MODULE = "uk_bin_collection.uk_bin_collection.councils.DoncasterCouncil"


def calendar_widget(events):
    """Build the calendar widget the way Liberty Create renders it.

    The council's widget is a Vue/FullCalendar component, and the platform
    passes it its whole event list in the container's data-params attribute,
    HTML-escaped. Only the current month is drawn into the grid.
    """
    params = {
        "settings": {"code_studio_widget_id": "CSC0000083GBSLB1"},
        "base_record_id": "154187",
        "is_vue_enabled": True,
        "template_data": {
            "events": [
                {
                    "id": 3415809 + index,
                    "title": title,
                    "date": date,
                    "color": "black",
                    "groupId": title,
                }
                for index, (title, date) in enumerate(events)
            ],
            "mats": {"csrf": "deadbeef"},
        },
    }
    return (
        '<div class="page_widget system_widget_code_studio_fixed" '
        'data-widget_id="56" data-instance_name="system_widget_code_studio_fixed" '
        f'data-params="{html.escape(json.dumps(params), quote=True)}">'
        f"{calendar_grid(events)}</div>"
    )


def calendar_grid(events, month="2026-10"):
    """Draw the FullCalendar month grid for the events that fall inside it."""
    days = sorted({date for _, date in events if date.startswith(month)})
    cells = ""
    for date in days:
        titles = "".join(
            '<a class="fc-event fc-daygrid-event"><div class="fc-event-main">'
            f'<div class="fc-event-title fc-sticky">{title}</div></div></a>'
            for title, event_date in events
            if event_date == date
        )
        cells += (
            f'<td role="gridcell" class="fc-day fc-daygrid-day" data-date="{date}">'
            '<div class="fc-daygrid-day-frame">'
            f'<div class="fc-daygrid-day-events">{titles}</div></div></td>'
        )
    return (
        '<div id="calendar" class="fc fc-media-screen">'
        '<h2 class="fc-toolbar-title">October 2026</h2>'
        f'<table class="fc-scrollgrid"><tbody><tr>{cells}</tr></tbody></table></div>'
    )


def service_listing(services):
    """Build the Day/Service table the app shows under the calendar.

    A service appears here as soon as the property is subscribed to it, even
    once its dates have run out, so the table must not be read for dates.
    """
    rows = "".join(
        '<tr class="page_fragment_collection">'
        f'<td><div class="page_fragment readonly">{day}</div></td>'
        f'<td><div class="page_fragment readonly">{service}</div></td></tr>'
        for day, service in services
    )
    return (
        '<div class="page_widget system_widget_foundation_listing">'
        f"<table><tbody>{rows}</tbody></table></div>"
    )


def results_page(events, services=()):
    """Assemble an address's collection page."""
    return (
        '<div class="page"><div class="page_widget system_widget">'
        "<span>Full Address</span>"
        "<span>The Laurels Nursing Home, High Street, Norton, "
        "Doncaster, DN6 9EU</span></div>"
        + calendar_widget(events)
        + service_listing(services)
        + "</div>"
    )


EVENTS = [
    ("Refuse", "2026-10-01"),
    ("Green Garden Waste Collection Service", "2026-10-08"),
    ("Recycling", "2026-10-08"),
    ("Refuse", "2026-10-15"),
    ("Recycling", "2026-11-05"),
]

RESULTS_HTML = results_page(
    EVENTS,
    services=[
        ("Thursday", "Refuse Waste Collection Service"),
        ("Thursday", "Green Garden Waste Collection Service"),
        ("Thursday", "Recycling Waste Collection Service"),
    ],
)

NO_COLLECTIONS_HTML = (
    '<div class="page"><div class="page_widget system_widget">'
    "<span>Full Address</span>"
    "<span>Civic Offices, Waterdale, , Doncaster, DN1 3BU</span>"
    "<p>There is no collection information available for this address. "
    "Please contact customer services on 01302 736000</p></div></div>"
)


def test_calendar_events_become_dated_collections():
    """Pair each waste type with its own date, in date order."""
    assert CouncilClass()._parse_collections(RESULTS_HTML) == {
        "bins": [
            {"type": "Refuse", "collectionDate": "01/10/2026"},
            {
                "type": "Green Garden Waste Collection Service",
                "collectionDate": "08/10/2026",
            },
            {"type": "Recycling", "collectionDate": "08/10/2026"},
            {"type": "Refuse", "collectionDate": "15/10/2026"},
            {"type": "Recycling", "collectionDate": "05/11/2026"},
        ]
    }


def test_every_published_month_is_read_not_just_the_rendered_one():
    """Read November's dates even though only October is drawn in the grid."""
    assert 'data-date="2026-11-05"' not in RESULTS_HTML
    assert {
        "type": "Recycling",
        "collectionDate": "05/11/2026",
    } in CouncilClass()._parse_collections(RESULTS_HTML)["bins"]


def test_a_subscribed_service_with_no_dates_is_not_reported():
    """Leave out a seasonal service whose dates have run out for the year."""
    html_without_garden = results_page(
        [event for event in EVENTS if "Garden" not in event[0]],
        services=[("Thursday", "Green Garden Waste Collection Service")],
    )
    bins = CouncilClass()._parse_collections(html_without_garden)["bins"]
    assert all("Garden" not in collection["type"] for collection in bins)
    assert len(bins) == 4


def test_repeated_events_are_collapsed():
    """Report one collection when the calendar lists a service twice over."""
    duplicated = results_page(EVENTS + [("Refuse", "2026-10-01")])
    assert (
        CouncilClass()
        ._parse_collections(duplicated)["bins"]
        .count({"type": "Refuse", "collectionDate": "01/10/2026"})
        == 1
    )


@pytest.mark.parametrize("bad_date", ["", "next Thursday", "2026-13-45"])
def test_unreadable_dates_are_skipped(bad_date):
    """Drop an event whose date cannot be read and keep the others."""
    bins = CouncilClass()._parse_collections(
        results_page(EVENTS + [("Bulky", bad_date)])
    )["bins"]
    assert all(collection["type"] != "Bulky" for collection in bins)
    assert len(bins) == 5


def test_untitled_events_are_skipped():
    """Drop an event with no waste type rather than reporting a blank bin."""
    bins = CouncilClass()._parse_collections(
        results_page(EVENTS + [("", "2026-12-03")])
    )["bins"]
    assert len(bins) == 5


def test_address_without_collections_raises():
    """Explain that the council holds no collections for the address."""
    with pytest.raises(ValueError, match="no collection information"):
        CouncilClass()._parse_collections(NO_COLLECTIONS_HTML)


def test_page_without_a_calendar_raises():
    """Fail clearly when neither a calendar nor the council's message is there."""
    with pytest.raises(ValueError, match="No collection calendar"):
        CouncilClass()._parse_collections("<html><body><p>Nothing</p></body></html>")


@pytest.mark.parametrize("params", ["not json at all", "{}", '{"template_data": []}'])
def test_unusable_widget_params_fall_back_to_the_rendered_grid(params):
    """Read the drawn month when the widget carries no usable event list."""
    broken = (
        '<div class="page_widget system_widget_code_studio_fixed" '
        f'data-params="{html.escape(params, quote=True)}">'
        f"{calendar_grid(EVENTS)}</div>"
    )
    assert CouncilClass()._parse_collections(broken) == {
        "bins": [
            {"type": "Refuse", "collectionDate": "01/10/2026"},
            {
                "type": "Green Garden Waste Collection Service",
                "collectionDate": "08/10/2026",
            },
            {"type": "Recycling", "collectionDate": "08/10/2026"},
            {"type": "Refuse", "collectionDate": "15/10/2026"},
        ]
    }


@pytest.mark.parametrize(
    "address, paon, score",
    [
        ("3 High Street Norton Doncaster DN6 9EU", "3", 2),
        ("13 High Street Norton Doncaster DN6 9EU", "3", 0),
        ("23 High Street Norton Doncaster DN6 9EU", "23", 2),
        ("Rear Of 23 High Street Norton Doncaster DN6 9EU", "23", 1),
        (
            "The Laurels Nursing Home High Street Norton Doncaster DN6 9EU",
            "The Laurels Nursing Home",
            2,
        ),
        (
            "Flat 2 Example House High Street Norton Doncaster DN6 9EU",
            "Example House",
            1,
        ),
        ("3 High Street Norton Doncaster DN6 9EU", "99", 0),
    ],
)
def test_addresses_are_matched_on_whole_words(address, paon, score):
    """Prefer the address that starts with the requested number or name."""
    assert CouncilClass()._match_score(address, paon) == score


def address_link(address, record_id):
    """Build a stand-in for a result row's collection details link."""
    link = MagicMock()
    link.get_attribute.side_effect = lambda name: {
        "aria-label": f"View collection details, {address}",
        "href": (
            "https://doncaster-wasterecycling.oncreate.app/w/webpage/"
            f"address-collections?webpage_token=abc&auth=def&id={record_id}"
        ),
    }.get(name)
    return link


def search_results():
    """Return two result rows, one of them the requested property."""
    return [
        address_link(
            "The Laurels Nursing Home High Street Norton Doncaster DN6 9EU", 154187
        ),
        address_link(
            "The Laurels Cottage High Street Norton Doncaster DN6 9EU", 154189
        ),
    ]


def test_parse_data_opens_the_matched_address_and_closes_the_driver():
    """Open the right address's calendar, parse it and close the browser."""
    driver = MagicMock()
    driver.page_source = RESULTS_HTML
    driver.find_elements.return_value = search_results()

    with patch(f"{MODULE}.create_webdriver", return_value=driver), patch(
        f"{MODULE}.check_postcode", return_value=True
    ), patch.object(CouncilClass, "wait_for_element_conditions"):
        result = CouncilClass().parse_data(
            "", postcode="DN6 9EU", paon="The Laurels Nursing Home"
        )

    assert result == CouncilClass()._parse_collections(RESULTS_HTML)
    assert driver.get.call_args_list[-1].args[0].endswith("id=154187")
    driver.quit.assert_called_once()


def test_parse_data_retries_without_the_property_filter():
    """Search the whole postcode when the property box matches nothing."""
    driver = MagicMock()
    driver.page_source = RESULTS_HTML
    driver.find_elements.side_effect = [[], search_results()]

    with patch(f"{MODULE}.create_webdriver", return_value=driver), patch(
        f"{MODULE}.check_postcode", return_value=True
    ), patch.object(CouncilClass, "wait_for_element_conditions"):
        CouncilClass().parse_data(
            "", postcode="DN6 9EU", paon="The Laurels Nursing Home"
        )

    assert driver.find_elements.call_count == 2
    assert driver.get.call_args_list[-1].args[0].endswith("id=154187")


def test_unmatched_address_names_what_the_search_found():
    """Name the addresses in the postcode so the user can correct their input."""
    driver = MagicMock()
    driver.find_elements.return_value = search_results()

    with patch(f"{MODULE}.create_webdriver", return_value=driver), patch(
        f"{MODULE}.check_postcode", return_value=True
    ), patch.object(CouncilClass, "wait_for_element_conditions"), pytest.raises(
        ValueError, match="No address matching '99'"
    ) as excinfo:
        CouncilClass().parse_data("", postcode="DN6 9EU", paon="99")

    assert "The Laurels Nursing Home" in str(excinfo.value)
    driver.quit.assert_called_once()


def test_parse_data_requires_a_house_number():
    """Ask for a house number instead of guessing at an address."""
    with patch(f"{MODULE}.create_webdriver") as webdriver, patch(
        f"{MODULE}.check_postcode", return_value=True
    ), pytest.raises(ValueError, match="house number or name"):
        CouncilClass().parse_data("", postcode="DN6 9EU")
    webdriver.assert_not_called()


def test_driver_is_closed_on_timeout():
    """Close the browser even when waiting for the page raises a timeout."""
    driver = MagicMock()
    with patch(f"{MODULE}.create_webdriver", return_value=driver), patch(
        f"{MODULE}.check_postcode", return_value=True
    ), patch.object(
        CouncilClass, "wait_for_element_conditions", side_effect=TimeoutException
    ), pytest.raises(
        TimeoutException
    ):
        CouncilClass().parse_data(
            "", postcode="DN6 9EU", paon="The Laurels Nursing Home"
        )
    driver.quit.assert_called_once()
