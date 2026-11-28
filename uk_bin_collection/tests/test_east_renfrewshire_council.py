"""Unit tests for East Renfrewshire's form, address and results parsing.

The council's iCM wizard is driven over plain HTTP (curl_cffi), since automated
Chrome is served a Cloudflare Turnstile challenge. Fixtures are cut down from
the live pages.
"""

import pytest

from uk_bin_collection.uk_bin_collection.councils.EastRenfrewshireCouncil import (
    parse_address_options,
    parse_form,
    parse_results,
    select_address,
)

ADDRESS_PAGE = """
<form id="cookie-consent-form" action="https://example.org/cookies"></form>
<form action="https://example.org/apiserver/formsservice/http/processsubmission?x=1&amp;y=2" method="post">
<input type="hidden" name="BINDAYSV2_NONCE" value="abc"/>
<input type="hidden" name="BINDAYSV2_PAGENAME" value="PAGE2"/>
<input type="hidden" id="BINDAYSV2_PAGE2_FIELD293" name="BINDAYSV2_PAGE2_FIELD293" value="true"/>
<select id="BINDAYSV2_PAGE2_UPRN" name="BINDAYSV2_PAGE2_UPRN" class="icmlselect">
<option value="" selected="selected">5 addresses found</option>
<option value="000131037807" >1 Woodvale Avenue Giffnock G46 6RG </option>
<option value="000131050775" >1A Woodvale Avenue Giffnock G46 6RG </option>
<option value="000131040273" >23 Woodvale Avenue Giffnock G46 6RG </option>
<option value="000131099999" >123 Woodvale Avenue Giffnock G46 6RG </option>
<option value="000131011111" >Flat 2 Woodvale House Giffnock G46 6RG </option>
</select>
<button class="btn" type="submit" name="BINDAYSV2_FORMACTION_NEXT" value="BINDAYSV2_PAGE2_FIELD294">Find</button>
</form>
"""

RESULTS_PAGE = """
<table style="width:100%" border="1"><tr><th scope="col">Date</th><th scope="col">Day</th><th scope="col">Bin Type</th></tr>
<tr><td>09/12/2026</td><td>Wednesday</td><td><img alt="x"/> Grey - General Waste</td></tr>
<tr><td>02/12/2026</td><td>Wednesday</td><td><img alt="x"/> Brown - Food and Garden waste<br><img alt="x"/> Blue - Paper and Cardboard recycling</td></tr>
</table>
"""


def test_parse_form_picks_wizard_form_and_unescapes_action():
    action, fields, button = parse_form(ADDRESS_PAGE)
    assert action.endswith("processsubmission?x=1&y=2")
    assert fields["BINDAYSV2_NONCE"] == "abc"
    assert fields["BINDAYSV2_PAGE2_FIELD293"] == "true"
    assert fields["BINDAYSV2_FORMACTION_NEXT"] == "BINDAYSV2_PAGE2_FIELD294"
    assert button == "BINDAYSV2_FORMACTION_NEXT"


def test_address_options_skip_the_placeholder():
    name, options = parse_address_options(ADDRESS_PAGE)
    assert name == "BINDAYSV2_PAGE2_UPRN"
    assert len(options) == 5
    assert options[0] == ("1 Woodvale Avenue Giffnock G46 6RG", "000131037807")


def test_house_number_matches_whole_number_at_start_only():
    _, options = parse_address_options(ADDRESS_PAGE)
    assert select_address(options, "1", None) == "000131037807"
    assert select_address(options, "23", None) == "000131040273"
    assert select_address(options, "1A", None) == "000131050775"
    assert select_address(options, "flat 2", None) == "000131011111"


def test_no_match_raises():
    _, options = parse_address_options(ADDRESS_PAGE)
    with pytest.raises(ValueError, match="found 0"):
        select_address(options, "3", None)


def test_ambiguous_match_raises_and_lists_candidates():
    _, options = parse_address_options(ADDRESS_PAGE)
    with pytest.raises(ValueError, match="found 2") as error:
        select_address(options + [("1 Other Road G46 6RG", "000000000001")], "1", None)
    assert "Other Road" in str(error.value)


def test_uprn_match_ignores_leading_zeros():
    _, options = parse_address_options(ADDRESS_PAGE)
    assert select_address(options, None, "131040273") == "000131040273"
    with pytest.raises(ValueError, match="found 0"):
        select_address(options, None, "42")


def test_no_house_number_or_uprn_raises_instead_of_guessing():
    _, options = parse_address_options(ADDRESS_PAGE)
    with pytest.raises(ValueError, match="house number"):
        select_address(options, None, None)


def test_results_split_multiple_bins_and_sort_by_date():
    bins = parse_results(RESULTS_PAGE)["bins"]
    assert bins == [
        {"type": "Brown - Food and Garden waste", "collectionDate": "02/12/2026"},
        {
            "type": "Blue - Paper and Cardboard recycling",
            "collectionDate": "02/12/2026",
        },
        {"type": "Grey - General Waste", "collectionDate": "09/12/2026"},
    ]


def test_missing_results_table_raises():
    with pytest.raises(ValueError, match="results table"):
        parse_results("<html><body>Just a moment...</body></html>")
