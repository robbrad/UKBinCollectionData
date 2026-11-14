"""Offline tests: Nuneaton must raise, not return a blank result, when it can't find a street."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import (
    NuneatonBedworthBoroughCouncil as module,
)

SEARCH_HTML = (
    '<a class="list__link" href="/streets/newdigate-road">Newdigate Road</a>'
    '<a class="list__link" href="/streets/newdigate-road-east">Newdigate Road East</a>'
    '<a class="list__link" href="/streets/high-street">High Street</a>'
    '<a class="list__link" href="/streets/high-street-bedworth">High Street Bedworth</a>'
)


def _response(html="", status=200):
    return SimpleNamespace(status_code=status, content=html.encode())


def _run(paon, search=None, street_page=None):
    """parse_data with the search page and street page stubbed out."""
    pages = {"search": search or _response(SEARCH_HTML)}

    def fake_get(url, headers=None):
        if "directory/search" in url:
            return pages["search"]
        return street_page or _response("")

    with patch.object(module.requests, "get", side_effect=fake_get):
        return module.CouncilClass().parse_data("", paon=paon)


def test_an_exact_street_name_wins_over_longer_names_that_contain_it():
    street_page = _response('<a href="/downloads/file/1/bin-calendar-monday-a">x</a>')
    data = _run("Newdigate Road", street_page=street_page)
    # Resolved to Newdigate Road alone (not "... East"), so a calendar was read
    assert data["bins"]
    assert all(b["collectionDate"].count("/") == 2 for b in data["bins"])


def test_an_ambiguous_street_lists_the_candidates_instead_of_returning_nothing():
    with pytest.raises(ValueError, match="More than one street.*High Street Bedworth"):
        _run("High")


def test_an_unknown_street_is_an_error_not_an_empty_result():
    with pytest.raises(ValueError, match="No street matching 'Nowhere Lane'"):
        _run("Nowhere Lane")


def test_a_failed_search_is_an_error_not_an_empty_result():
    with pytest.raises(ConnectionError, match="search failed.*503"):
        _run("Newdigate Road", search=_response(status=503))


def test_a_street_page_without_a_calendar_link_is_an_error():
    with pytest.raises(ValueError, match="No bin calendar download link"):
        _run("Newdigate Road", street_page=_response("<p>nothing here</p>"))


def test_an_unrecognised_calendar_is_reported_not_a_key_error():
    street_page = _response('<a href="/downloads/file/9/bin-calendar-new-round">x</a>')
    with pytest.raises(ValueError, match="bin-calendar-new-round.*not one this"):
        _run("Newdigate Road", street_page=street_page)


def test_a_failed_street_page_is_an_error():
    with pytest.raises(ConnectionError, match="street page failed.*500"):
        _run("Newdigate Road", street_page=_response(status=500))
