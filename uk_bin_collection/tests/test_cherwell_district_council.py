"""Unit tests for Cherwell's results-page parser.

The fixture is reduced from the live forms.cherwell.gov.uk/myaccount?uprn=...
markup. The search moved there from www.cherwell.gov.uk, which now renders no
results at all, and the parser used to return an empty list for that.
"""

from datetime import date

import pytest

from uk_bin_collection.uk_bin_collection.councils.CherwellDistrictCouncil import (
    CouncilClass,
)

TODAY = date(2026, 11, 28)


def _task(colour: str, day_text: str) -> str:
    return f"""
    <li class="list__item"><div class="boxed">
      <h3 class="bin-collection-tasks__heading">
        <span class="visually-hidden">Your next</span> {colour} Bin
        <span class="visually-hidden">collection</span>
      </h3>
      <div class="bin-collection-tasks__content">
        <p class="bin-collection-tasks__day">Wednesday</p>
        <p class="bin-collection-tasks__date">{day_text}</p>
      </div></div></li>"""


def _page(*tasks: str) -> str:
    return f"""<div class="bin-collection-results">
      <div class="bin-collection-results__tasks"><ul class="list bin-collection-tasks">
      {"".join(tasks)}</ul></div></div>"""


def test_parses_types_and_dates_sorted():
    html = _page(_task("Green", "9th December"), _task("Brown", "2nd December"))
    assert CouncilClass.parse_results(html, TODAY) == {
        "bins": [
            {"type": "Brown Bin", "collectionDate": "02/12/2026"},
            {"type": "Green Bin", "collectionDate": "09/12/2026"},
        ]
    }


def test_collection_today_stays_this_year():
    html = _page(_task("Blue", "28th November"))
    assert CouncilClass.parse_results(html, TODAY)["bins"][0]["collectionDate"] == (
        "28/11/2026"
    )


def test_past_date_rolls_to_next_year():
    html = _page(_task("Blue", "2nd January"))
    assert CouncilClass.parse_results(html, TODAY)["bins"][0]["collectionDate"] == (
        "02/01/2027"
    )


def test_page_without_results_raises():
    with pytest.raises(ValueError, match="No bin collection results"):
        CouncilClass.parse_results("<html><main>Find your bins</main></html>", TODAY)


def test_results_block_without_bins_raises():
    with pytest.raises(ValueError, match="no bin collections"):
        CouncilClass.parse_results(_page(), TODAY)
