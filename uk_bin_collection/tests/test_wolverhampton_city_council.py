"""Wolverhampton's results page changed layout in October 2026 (#2334).

Its service columns went from col-md-4 to col-md-3 and the date line from
"Next date: October 27, 2026" to a bare "October 27", so the scraper found nothing
and returned a blank result. Markup is reduced from the layouts described in #2310.
"""

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import WolverhamptonCityCouncil as wcc

TODAY = date(2026, 10, 15)


def service(name, date_line, col="col-md-3"):
    return f'<div class="{col}"><h3>{name}</h3><h4>{date_line}</h4><h4>Day: Tuesday</h4></div>'


def page(*columns):
    return f'<div class="jumbotron"><div class="row">{"".join(columns)}</div></div>'


NEW_LAYOUT = page(
    service("Food waste", "October 27"),
    service("Recycling", "October 20"),
    service("General waste", "October 27"),
)
OLD_LAYOUT = page(
    service("Food waste", "Next date: October 27, 2026", col="col-md-4"),
    service("Recycling", "Next date: October 20, 2026", col="col-md-4"),
)


def test_the_new_layout_with_yearless_dates_is_parsed_and_sorted():
    assert wcc._parse_collections(NEW_LAYOUT, TODAY) == [
        {"type": "Recycling", "collectionDate": "20/10/2026"},
        {"type": "Food waste", "collectionDate": "27/10/2026"},
        {"type": "General waste", "collectionDate": "27/10/2026"},
    ]


def test_the_old_layout_still_parses():
    assert wcc._parse_collections(OLD_LAYOUT, TODAY) == [
        {"type": "Recycling", "collectionDate": "20/10/2026"},
        {"type": "Food waste", "collectionDate": "27/10/2026"},
    ]


def test_an_outer_wrapper_column_does_not_mislabel_a_service():
    # The first service has no date (e.g. suspended). Read naively, the outer
    # wrapper would pair that first heading with the NEXT service's date, which
    # de-duplication can't catch because it is a wrong entry, not a repeat.
    html = (
        '<div class="jumbotron"><div class="col-12">'
        '<div class="col-md-3"><h3>Garden waste</h3><h4>Day: Tuesday</h4></div>'
        + service("Recycling", "October 20")
        + "</div></div>"
    )
    assert wcc._parse_collections(html, TODAY) == [
        {"type": "Recycling", "collectionDate": "20/10/2026"}
    ]


def test_the_same_service_and_date_is_only_reported_once():
    html = page(
        service("Food waste", "October 27"), service("Food waste", "October 27")
    )
    assert len(wcc._parse_collections(html, TODAY)) == 1


@pytest.mark.parametrize(
    "text, today, expected",
    [
        ("October 27", date(2026, 10, 15), date(2026, 10, 27)),
        ("October 15", date(2026, 10, 15), date(2026, 10, 15)),  # today counts
        ("January 5", date(2026, 12, 20), date(2027, 1, 5)),  # rolls into next year
        ("December 28", date(2026, 12, 20), date(2026, 12, 28)),
        (
            "October 27, 2026",
            date(2026, 12, 1),
            date(2026, 10, 27),
        ),  # explicit year wins
        ("Day: Tuesday", date(2026, 10, 15), None),
        ("", date(2026, 10, 15), None),
    ],
)
def test_dates_with_or_without_a_year(text, today, expected):
    assert wcc._parse_date(text, today) == expected


def test_a_page_with_no_dates_is_an_error_not_an_empty_result():
    with pytest.raises(ValueError, match="No bin collection dates"):
        wcc._parse_collections(page("<div class='col-md-3'><h3>Food</h3></div>"), TODAY)
    with pytest.raises(ValueError, match="Could not find bin collection data"):
        wcc._parse_collections("<p>maintenance</p>", TODAY)


OPTIONS = [
    {"uprn": "1", "label": "1, WESTLAND ROAD, WOLVERHAMPTON, WV3 9NZ"},
    {"uprn": "11", "label": "11, WESTLAND ROAD, WOLVERHAMPTON, WV3 9NZ"},
    {"uprn": "1A", "label": "1A, WESTLAND ROAD, WOLVERHAMPTON, WV3 9NZ"},
    {"uprn": "F1", "label": "FLAT 1, 12 WESTLAND ROAD, WOLVERHAMPTON, WV3 9NZ"},
    {"uprn": "F10", "label": "FLAT 10, 12 WESTLAND ROAD, WOLVERHAMPTON, WV3 9NZ"},
    {"uprn": "20", "label": "20, WESTLAND ROAD, WOLVERHAMPTON, WV3 9NZ"},
]


@pytest.mark.parametrize(
    "paon, uprn",
    [
        ("1", "1"),
        ("11", "11"),
        ("1a", "1A"),
        ("20", "20"),
        ("Flat 1", "F1"),
        ("flat 10", "F10"),
    ],
)
def test_the_house_number_picks_that_address_only(paon, uprn):
    assert wcc._match_address(OPTIONS, paon, "WV3 9NZ") == uprn


@pytest.mark.parametrize("paon", ["2", "12", "WESTLAND", "Flat 2"])
def test_a_number_that_is_not_the_start_of_an_address_is_refused(paon):
    # "12" and "WESTLAND" appear inside labels but start none; "2" is only a prefix of "20"
    with pytest.raises(ValueError, match="Could not match"):
        wcc._match_address(OPTIONS, paon, "WV3 9NZ")


def test_two_addresses_starting_the_same_way_are_an_error_not_a_guess():
    options = OPTIONS + [{"uprn": "X", "label": "1, WESTLAND CLOSE, WV3 9NZ"}]
    with pytest.raises(ValueError, match="More than one address starts '1'"):
        wcc._match_address(options, "1", "WV3 9NZ")


def test_without_a_house_number_only_a_sole_address_is_accepted():
    assert wcc._match_address(OPTIONS[:1], "", "WV3 9NZ") == "1"
    with pytest.raises(ValueError, match="6 addresses found"):
        wcc._match_address(OPTIONS, None, "WV3 9NZ")


def test_parse_data_fetches_the_results_page_for_the_uprn_and_postcode():
    soon = datetime.now().date() + timedelta(days=3)
    html = page(service("Food waste", soon.strftime("%B %d")))
    response = MagicMock(content=html.encode())
    with patch.object(wcc.requests, "get", return_value=response) as get, patch.object(
        wcc, "check_postcode", return_value=True
    ):
        data = wcc.CouncilClass().parse_data(
            "", uprn="100071205205", postcode="WV3 9NZ"
        )
    assert get.call_args.args[0].endswith("/find-my-nearest/WV3%209NZ/100071205205")
    assert data == {
        "bins": [{"type": "Food waste", "collectionDate": soon.strftime("%d/%m/%Y")}]
    }
