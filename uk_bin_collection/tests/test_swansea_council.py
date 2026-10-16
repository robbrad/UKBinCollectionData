"""Unit tests for the Swansea recycling search scraper.

Swansea moved its collection search from the ASP.NET page at
www1.swansea.gov.uk (abandoned, 502 to everything) to a GOSS iCM form at
www.swansea.gov.uk/recyclingsearch. These tests drive the new flow from
saved snippets of the real pages, so the page shape is pinned without
touching the network.

The address check matters most: the old search could answer a failed
lookup with the *previous* search's result, so the scraper must refuse a
results page that is about a different address rather than report another
household's collection days.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import SwanseaCouncil
from uk_bin_collection.uk_bin_collection.councils.SwanseaCouncil import CouncilClass

POSTCODE = "SA4 3PQ"

FORM_ACTION = (
    "https://www.swansea.gov.uk/apiserver/formsservice/http/processsubmission"
    "?pageSessionId=page-1&fsid=session-1&fsn=nonce-1"
)

FORM_PAGE = f"""
<html><body>
  <form id="RECYCLINGSEARCHMYACCOUNT_FORM" action="{FORM_ACTION}" method="post">
    <input type="hidden" name="RECYCLINGSEARCHMYACCOUNT_PAGESESSIONID" value="page-1" />
    <input type="hidden" name="RECYCLINGSEARCHMYACCOUNT_SESSIONID" value="session-1" />
    <input type="hidden" name="RECYCLINGSEARCHMYACCOUNT_NONCE" value="nonce-1" />
    <input type="hidden" name="RECYCLINGSEARCHMYACCOUNT_VARIABLES" value="" />
    <input type="text" name="RECYCLINGSEARCHMYACCOUNT_ADDRESSLOOKUPPOSTCODE" value="" />
    <input type="button" name="RECYCLINGSEARCHMYACCOUNT_ADDRESSLOOKUPSEARCH"
           value="Find address" />
    <select name="RECYCLINGSEARCHMYACCOUNT_ADDRESSLOOKUPADDRESS"></select>
    <input type="text" name="RECYCLINGSEARCHMYACCOUNT_ADDRESSLINE1" value="" />
    <input type="text" name="RECYCLINGSEARCHMYACCOUNT_ADDRESSLINE2" value="" />
    <input type="text" name="RECYCLINGSEARCHMYACCOUNT_ADDRESSLINE3" value="" />
    <input type="text" name="RECYCLINGSEARCHMYACCOUNT_TOWN" value="" />
    <input type="text" name="RECYCLINGSEARCHMYACCOUNT_POSTCODE" value="" />
    <input type="hidden" name="RECYCLINGSEARCHMYACCOUNT_UPRN" value="" />
  </form>
</body></html>
"""


def address(line1, udprn, postcode=POSTCODE):
    return {
        "udprn": udprn,
        "line1": line1,
        "line2": "THREE CROSSES",
        "line3": "",
        "town": "SWANSEA",
        "postcode": postcode,
    }


ADDRESSES = [
    address("1 ORCHARD DRIVE", "200002958839"),
    address("14 ORCHARD DRIVE", "100100324821"),
    address("15 ORCHARD DRIVE", "100100324822"),
]


def lookup_body(addresses=None):
    """The JSONP the postcode endpoint answers with."""
    if addresses is None:
        addresses = ADDRESSES
    payload = {"jsonrpc": "2.0", "id": 1, "result": addresses}
    return f"cb({json.dumps(payload)})"


def results_page(
    shown_address="14 ORCHARD DRIVE, THREE CROSSES, SWANSEA, SA4 3PQ",
    pink="16/10/2026",
    green="23/10/2026",
    calendars=(("October 2026", (("16", "pink"), ("23", "green"), ("30", "pink"))),),
):
    """A cut-down copy of the real results page markup."""
    tables = ""
    for caption, days in calendars:
        cells = "".join(
            f'<td class="calendar-{colour}">{day}</td>' for day, colour in days
        )
        tables += (
            f'<table class="bin-calendar"><caption>{caption}</caption>'
            f"<tbody><tr>{cells}</tr>"
            f'<tr><td class="calendar-empty"></td></tr></tbody></table>'
        )
    return f"""
    <html><body>
      <div id="RECYCLINGSEARCHMYACCOUNT_DISPLAYBININFO" class="htmltemplate">
        <p class="nvp nvp--address">
          <span class="nvp__label">Address</span>
          <span class="nvp__value"><strong>{shown_address}</strong></span>
        </p>
        <article class="myaccount-block__collection myaccount-block__collection--green">
          <h3 class="myaccount-block__title">Green week</h3>
          <p class="myaccount-block__date myaccount-block__date--green">{green}</p>
        </article>
        <article class="myaccount-block__collection myaccount-block__collection--pink">
          <h3 class="myaccount-block__title">Pink week</h3>
          <p class="myaccount-block__date myaccount-block__date--pink">{pink}</p>
        </article>
      </div>
      <div class="bin-calendar-wrap">{tables}</div>
    </body></html>
    """


# Swansea answers a property it has no round for with an empty block.
NO_DETAILS_PAGE = (
    '<html><body><div id="RECYCLINGSEARCHMYACCOUNT_DISPLAYBININFO">'
    "<p>No collection details returned.</p></div></body></html>"
)


def run(results=None, lookup=None, form=FORM_PAGE, **kwargs):
    """Drive parse_data with the network replaced by saved pages."""
    session = MagicMock()
    session.get.side_effect = [
        MagicMock(text=form),
        MagicMock(text=lookup if lookup is not None else lookup_body()),
    ]
    session.post.return_value = MagicMock(
        text=results if results is not None else results_page()
    )
    with patch.object(
        SwanseaCouncil.cffi_requests, "Session", return_value=session
    ), patch.object(SwanseaCouncil, "check_postcode", return_value=True):
        kwargs.setdefault("postcode", POSTCODE)
        return CouncilClass().parse_data("", **kwargs), session


def test_returns_every_date_the_page_offers():
    """The cards give the next date per colour, the calendars a full year."""
    data, _ = run(paon="14")

    assert data["bins"] == [
        {"type": "Pink Week", "collectionDate": "16/10/2026"},
        {"type": "Green Week", "collectionDate": "23/10/2026"},
        {"type": "Pink Week", "collectionDate": "30/10/2026"},
    ]


def test_merges_several_calendar_months_without_duplicating_the_cards():
    data, _ = run(
        paon="14",
        results=results_page(
            calendars=(
                ("October 2026", (("16", "pink"), ("23", "green"))),
                ("November 2026", (("6", "green"), ("13", "pink"))),
            )
        ),
    )

    assert data["bins"] == [
        {"type": "Pink Week", "collectionDate": "16/10/2026"},
        {"type": "Green Week", "collectionDate": "23/10/2026"},
        {"type": "Green Week", "collectionDate": "06/11/2026"},
        {"type": "Pink Week", "collectionDate": "13/11/2026"},
    ]


def test_a_day_marked_for_both_colours_yields_both_collections():
    data, _ = run(
        paon="14",
        results=results_page(
            pink="16/10/2026",
            green="16/10/2026",
            calendars=(("October 2026", (("16", "both"),)),),
        ),
    )

    assert data["bins"] == [
        {"type": "Green Week", "collectionDate": "16/10/2026"},
        {"type": "Pink Week", "collectionDate": "16/10/2026"},
    ]


def test_falls_back_to_the_cards_when_there_is_no_calendar():
    data, _ = run(paon="14", results=results_page(calendars=()))

    assert data["bins"] == [
        {"type": "Pink Week", "collectionDate": "16/10/2026"},
        {"type": "Green Week", "collectionDate": "23/10/2026"},
    ]


def test_posts_the_chosen_address_back_to_the_forms_service():
    _, session = run(paon="14")

    (url,) = session.post.call_args.args
    sent = session.post.call_args.kwargs["data"]
    assert url == FORM_ACTION
    assert sent["RECYCLINGSEARCHMYACCOUNT_ADDRESSLINE1"] == "14 ORCHARD DRIVE"
    assert sent["RECYCLINGSEARCHMYACCOUNT_UPRN"] == "100100324821"
    assert sent["RECYCLINGSEARCHMYACCOUNT_POSTCODE"] == POSTCODE
    # The select posts back the address's index in the lookup results.
    assert sent["RECYCLINGSEARCHMYACCOUNT_ADDRESSLOOKUPADDRESS"] == "1"
    assert sent["RECYCLINGSEARCHMYACCOUNT_NONCE"] == "nonce-1"
    assert (
        sent["RECYCLINGSEARCHMYACCOUNT_FORMACTION_NEXT"]
        == "RECYCLINGSEARCHMYACCOUNT_NEXTBUTTON"
    )
    # type="button" is not a successful control, so the browser never sends
    # it; posting it back re-runs the lookup instead of showing results.
    assert "RECYCLINGSEARCHMYACCOUNT_ADDRESSLOOKUPSEARCH" not in sent


def test_rejects_a_results_page_about_a_different_address():
    """The bug this guards: reporting a neighbour's collection days."""
    with pytest.raises(ValueError, match="different address"):
        run(
            paon="14",
            results=results_page(
                shown_address="1 ORCHARD DRIVE, THREE CROSSES, SWANSEA, SA4 3PQ"
            ),
        )


def test_rejects_a_results_page_about_a_different_postcode():
    with pytest.raises(ValueError, match="different address"):
        run(
            paon="14",
            results=results_page(
                shown_address="14 ORCHARD DRIVE, THREE CROSSES, SWANSEA, SA1 3SN"
            ),
        )


def test_raises_when_the_council_has_no_round_for_the_address():
    with pytest.raises(ValueError, match="no collection details"):
        run(paon="14", results=NO_DETAILS_PAGE)


def test_raises_when_the_page_has_an_address_but_no_dates():
    with pytest.raises(ValueError, match="No collection dates found"):
        run(paon="14", results=results_page(pink="", green="", calendars=()))


def test_a_house_number_does_not_match_a_longer_one():
    """'1' must not silently pick up '14 ORCHARD DRIVE'."""
    with pytest.raises(ValueError, match="Could not find house name/number '2'"):
        run(paon="2")


def test_an_ambiguous_house_name_is_refused_rather_than_guessed():
    lookup = lookup_body(
        [
            address("THE COTTAGE", "1"),
            address("THE COTTAGE ANNEXE", "2"),
        ]
    )
    with pytest.raises(ValueError, match="matches more than one address"):
        run(paon="THE COTTAGE", lookup=lookup)


def test_a_house_name_matches_on_a_word_boundary():
    lookup = lookup_body([address("LANE COTTAGE", "100100324821")])
    data, _ = run(
        paon="Lane Cottage",
        lookup=lookup,
        results=results_page(
            shown_address="LANE COTTAGE, THREE CROSSES, SWANSEA, SA4 3PQ"
        ),
    )

    assert len(data["bins"]) == 3


def test_a_uprn_still_works_for_existing_configurations():
    data, session = run(uprn="100100324821")

    assert len(data["bins"]) == 3
    sent = session.post.call_args.kwargs["data"]
    assert sent["RECYCLINGSEARCHMYACCOUNT_ADDRESSLINE1"] == "14 ORCHARD DRIVE"


def test_an_unmatched_uprn_says_to_use_a_house_number():
    """The lookup's identifier is a UDPRN for some properties, not a UPRN."""
    with pytest.raises(ValueError, match="set the house number instead"):
        run(uprn="10009999999")


def test_requires_a_house_number_or_a_uprn():
    with pytest.raises(ValueError, match="house name/number is required"):
        run()


def test_reports_an_invalid_postcode_from_the_lookup():
    lookup = lookup_body([{"Error": "1", "Description": "Invalid postcode"}])
    with pytest.raises(ValueError, match="Invalid postcode"):
        run(paon="14", lookup=lookup)


def test_reports_a_postcode_with_no_addresses():
    with pytest.raises(ValueError, match="No addresses found"):
        run(paon="14", lookup=lookup_body([]))


def test_reports_an_error_object_from_the_lookup():
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"message": "Bad request"}})
    with pytest.raises(ValueError, match="Bad request"):
        run(paon="14", lookup=f"cb({body})")


def test_reads_a_lookup_response_that_is_not_wrapped_in_a_callback():
    data, _ = run(
        paon="14",
        lookup=json.dumps({"jsonrpc": "2.0", "id": 1, "result": ADDRESSES}),
    )

    assert len(data["bins"]) == 3


def test_raises_a_clear_error_if_the_form_moves_again():
    with pytest.raises(ValueError, match="Could not find the recycling search form"):
        run(paon="14", form="<html><body><p>Page not found</p></body></html>")


def test_still_reads_the_calendar_when_the_cards_are_incomplete():
    """One colour's card missing entirely, the other missing its date."""
    page = """
    <html><body>
      <p class="nvp nvp--address">
        <span class="nvp__value">
          <strong>14 ORCHARD DRIVE, THREE CROSSES, SWANSEA, SA4 3PQ</strong>
        </span>
      </p>
      <article class="myaccount-block__collection myaccount-block__collection--pink">
        <h3 class="myaccount-block__title">Pink week</h3>
      </article>
      <table class="bin-calendar"><caption>October 2026</caption>
        <tbody><tr><td class="calendar-green">23</td></tr></tbody>
      </table>
    </body></html>
    """
    data, _ = run(paon="14", results=page)

    assert data["bins"] == [{"type": "Green Week", "collectionDate": "23/10/2026"}]


def test_ignores_a_calendar_whose_caption_is_not_a_month():
    data, _ = run(
        paon="14",
        results=results_page(
            calendars=(
                ("Collection calendar", (("16", "pink"),)),
                ("October 2026", (("23", "green"),)),
            )
        ),
    )

    assert {bin["collectionDate"] for bin in data["bins"]} == {
        "16/10/2026",
        "23/10/2026",
    }
