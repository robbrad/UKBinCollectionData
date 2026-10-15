"""The Ceredigion postcode-form link must be found however its label is marked up."""

from lxml import html

from uk_bin_collection.uk_bin_collection.councils.CeredigionCountyCouncil import (
    POSTCODE_SEARCH_LINK_XPATH,
)

HREF = "http://forms.ceredigion.gov.uk/ufs/ufsmain?formid=REFUSE_ROUTES"

# How the page markup looks now: the label sits in a nested <span>, which is
# what broke the old `contains(text(), 'Postcode Search')` selector.
NESTED_LABEL = f"""
<div>
  <p>You can use our <a href="{HREF}"><span>Postcode Search</span></a></p>
</div>
"""

# How it looked before, with the label as the anchor's own text node.
BARE_LABEL = f"""
<div>
  <p>You can use our <a href="{HREF}">Postcode Search</a></p>
</div>
"""

OLD_XPATH = "//a[contains(text(), 'Postcode Search')]"


def _find(markup, xpath):
    return html.fromstring(markup).xpath(xpath)


def test_the_link_is_found_when_its_label_is_wrapped_in_a_span():
    found = _find(NESTED_LABEL, POSTCODE_SEARCH_LINK_XPATH)
    assert len(found) == 1
    assert found[0].get("href") == HREF


def test_the_link_is_still_found_with_a_bare_label():
    found = _find(BARE_LABEL, POSTCODE_SEARCH_LINK_XPATH)
    assert len(found) == 1
    assert found[0].get("href") == HREF


def test_the_old_selector_really_did_miss_the_nested_label():
    # Pins the regression this selector exists to avoid: text() sees only an
    # element's own direct text nodes, so the span moved the label out of the
    # anchor's reach and the scraper timed out waiting for a link that was
    # plainly on the page.
    assert _find(BARE_LABEL, OLD_XPATH) != []
    assert _find(NESTED_LABEL, OLD_XPATH) == []


def test_the_link_is_found_when_the_label_is_translated():
    # The href carries the match, so a Welsh label still resolves.
    welsh = NESTED_LABEL.replace("Postcode Search", "Chwilio Cod Post")
    found = _find(welsh, POSTCODE_SEARCH_LINK_XPATH)
    assert len(found) == 1
    assert found[0].get("href") == HREF


def test_the_label_still_matches_if_the_form_id_changes():
    # The fallback half of the selector: a renamed form id shouldn't be fatal
    # while the English label is intact.
    renamed = NESTED_LABEL.replace("REFUSE_ROUTES", "WASTE_ROUNDS")
    found = _find(renamed, POSTCODE_SEARCH_LINK_XPATH)
    assert len(found) == 1


def test_an_unrelated_link_is_not_matched():
    other = '<div><a href="/resident/bins-recycling/">Bins &amp; Recycling</a></div>'
    assert _find(other, POSTCODE_SEARCH_LINK_XPATH) == []


# --- results parsing -------------------------------------------------------
#
# Mirrors the live results form for SY23 4RQ. Each schedule panel sits inside
# its own auto-generated "eb-<hash>-panel" wrapper, which is what scopes
# find_next_siblings to that panel's own bin types. Keep that nesting: flatten
# it and the first panel claims every waste_image on the page, producing
# duplicate bins with the wrong dates.

from datetime import datetime as real_datetime
from unittest.mock import MagicMock, patch

from uk_bin_collection.uk_bin_collection.councils import CeredigionCountyCouncil

MODULE_PATH = "uk_bin_collection.uk_bin_collection.councils.CeredigionCountyCouncil"


def _panel(schedule, when, bins):
    blocks = "".join(f'<div class="waste_image"><span>{b}</span></div>' for b in bins)
    return (
        f'<div class="CTID-x eb-{abs(hash(schedule)) % 99999}-panel">'
        f'  <div class="mb-3"><span>{schedule}</span>'
        f"  <span>Next collection: {when}</span></div>"
        f"  {blocks}"
        f"</div>"
    )


RESULTS_HTML = (
    "<div>"
    + _panel(
        "Weekly, every Monday",
        "Monday 19th October",
        ["Clear Recycling Bag", "Food Waste"],
    )
    + _panel(
        "Every 3 weeks",
        "Monday 2nd November",
        ["Non-Recyclable Waste", "Glass Bottles and Jars"],
    )
    + "</div>"
)


def parse_results(html):
    """Drive parse_data far enough to exercise the results parser."""
    element = MagicMock()
    element.get_attribute.return_value = html

    fake_wait = MagicMock()
    fake_wait.return_value.until.return_value = element

    with patch(f"{MODULE_PATH}.create_webdriver", return_value=MagicMock()), patch(
        f"{MODULE_PATH}.WebDriverWait", fake_wait
    ), patch(f"{MODULE_PATH}.Select"), patch(f"{MODULE_PATH}.EC"), patch(
        f"{MODULE_PATH}.check_paon"
    ), patch(
        f"{MODULE_PATH}.check_postcode"
    ), patch(
        f"{MODULE_PATH}.sleep"
    ):
        return CeredigionCountyCouncil.CouncilClass().parse_data(
            "", paon="BLAEN CWMMAGWR", postcode="SY23 4RQ", headless=True
        )


def test_every_schedule_panel_contributes_its_own_bins():
    year = real_datetime.now().year
    assert parse_results(RESULTS_HTML) == {
        "bins": [
            {"type": "Clear Recycling Bag", "collectionDate": f"19/10/{year}"},
            {"type": "Food Waste", "collectionDate": f"19/10/{year}"},
            {"type": "Non-Recyclable Waste", "collectionDate": f"02/11/{year}"},
            {"type": "Glass Bottles and Jars", "collectionDate": f"02/11/{year}"},
        ]
    }


def test_a_second_schedule_panel_is_not_dropped():
    # Regression guard: the parser used to match one auto-generated panel class
    # and silently lose every other schedule.
    types = [b["type"] for b in parse_results(RESULTS_HTML)["bins"]]
    assert "Non-Recyclable Waste" in types, "the 'Every 3 weeks' panel was dropped"


def test_ordinal_suffixes_are_tolerated():
    for suffix in ("1st", "2nd", "3rd", "4th"):
        html = RESULTS_HTML.replace("19th", suffix)
        day = suffix[:-2].zfill(2)
        assert parse_results(html)["bins"][0]["collectionDate"].startswith(f"{day}/10/")


def test_a_panel_without_a_parsable_date_is_skipped():
    html = RESULTS_HTML.replace(
        "Next collection: Monday 2nd November", "Next collection: TBC"
    )
    types = [b["type"] for b in parse_results(html)["bins"]]
    assert types == ["Clear Recycling Bag", "Food Waste"]


def test_no_panels_at_all_yields_no_bins():
    assert parse_results("<div><p>Nothing here</p></div>") == {"bins": []}
