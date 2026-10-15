"""Offline tests for KnowsleyMBCouncil parsing.

The live CI run returned no bins: the Mendix page renders the
"<colour> bin next collection date" labels with empty ``&nbsp;`` values before
the data loads, and the scraper used to parse as soon as the labels appeared.
"""

from uk_bin_collection.uk_bin_collection.councils.KnowsleyMBCouncil import (
    _has_collection_dates,
    _parse_bin_info,
)


def _field(label, value):
    return (
        '<div class="mx-textbox form-group no-columns">'
        f'<label class="control-label">{label}</label>'
        f'<div class="form-control-static">{value}</div>'
        "</div>"
    )


def _page(maroon, grey, blue, food="&nbsp;"):
    return (
        '<div class="mx-dataview-content">'
        + _field("Maroon bin next collection date", maroon)
        + _field("Grey bin next collection date", grey)
        + _field("Blue bin next collection date", blue)
        + _field("Next food caddy collection date", food)
        + "</div>"
    )


# Structure as captured from the live CI run (values not yet loaded).
EMPTY_PAGE = _page("&nbsp;", "&nbsp;", "&nbsp;")


def test_empty_form_is_not_treated_as_loaded():
    assert _has_collection_dates(EMPTY_PAGE) is False
    assert _parse_bin_info(EMPTY_PAGE) == {"bins": []}


def test_populated_form_is_parsed_and_sorted():
    html = _page("Monday 26/10/2026", "Monday 19/10/2026", "&nbsp;")
    assert _has_collection_dates(html) is True
    assert _parse_bin_info(html) == {
        "bins": [
            {"type": "Grey", "collectionDate": "19/10/2026"},
            {"type": "Maroon", "collectionDate": "26/10/2026"},
        ]
    }
