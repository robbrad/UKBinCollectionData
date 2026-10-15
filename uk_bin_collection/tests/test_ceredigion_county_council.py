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
