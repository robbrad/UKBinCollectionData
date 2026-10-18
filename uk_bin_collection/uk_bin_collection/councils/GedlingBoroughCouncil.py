"""Gedling Borough Council.

Gedling now publishes bin days through a Netcall Liberty Create portal at
waste.digital.gedling.gov.uk ("Find your bin collection days"). The
gbcbincalendars.co.uk API this scraper used before reads the old calendars:
it takes 30-45 seconds to answer, a bare postcode always fails, and many
addresses fail with "Failed to get yearly calendar page".

The portal draws its pages with JavaScript, but fetches each page's content
with a plain POST carrying the page's form token, so no browser is needed:

1. GET the page for its form token (``"csrf":"..."``), then POST for the
   address form.
2. Search the postcode through the address field's ``search`` action, which
   returns the addresses with the portal's own ids (not UPRNs).
3. Submit the form with the chosen id; the portal answers with a redirect
   to that address's next four weeks of collections, a table of services
   and dates.

The address is chosen by its start: the house number or name in
``house_number`` ("11", "Rose Cottage"), or the start of the street address
("11 Gedling Road").
"""

import json
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import (
    date_format,
    get_scraper_user_agent,
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://waste.digital.gedling.gov.uk"
PAGE = "/w/webpage/bin-collections"

# The portal's ids for the address form's parts
SEARCH_CELL = "PCL0004494GBSHB1"
ADDRESS_FIELD = "PCF0016554GBSHB1"
MANUAL_ADDRESS_FIELD = "PCF0016553GBSHB1"
# The browser leaves the type-ahead box out of its submit; sending it (even
# empty) makes the portal answer with an empty page
TYPE_AHEAD_FIELD = "PCF0014909GBSHB1"
SUBMIT_FIELD = "PCF0015021GBSHB1"

TIMEOUT = 30


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        postcode = (kwargs.get("postcode") or "").strip()
        house = (kwargs.get("paon") or "").strip()
        if not postcode or not house:
            raise ValueError(
                "Gedling needs a postcode and a house number or name, "
                "e.g. postcode 'NG5 6NQ' and house number '11'."
            )

        self.session = requests.Session()
        self.session.headers["User-Agent"] = get_scraper_user_agent()

        form, token, own_url = self._open_form()
        fields = self._form_fields(form)
        addresses = self._search(postcode, token, own_url, fields["submitted_page_id"])
        if not addresses:
            raise ValueError(f"Gedling found no addresses for postcode {postcode}")
        address_id = self._choose(addresses, house)

        data = {name: value for name, value in fields.items() if TYPE_AHEAD_FIELD not in name}
        prefix = next(name for name in fields if SEARCH_CELL in name).rsplit("[", 1)[0]
        submit = form.find("input", attrs={"name": re.compile(SUBMIT_FIELD)})
        data.update(
            {
                f"{prefix}[{ADDRESS_FIELD}]": address_id,
                f"{prefix}[{MANUAL_ADDRESS_FIELD}]": "0",
                "form_check": token,
                submit["name"]: submit.get("value", ""),
                "submit_fragment_id": SUBMIT_FIELD,
            }
        )
        answer = self._post(own_url, data, token, stack=[PAGE.lstrip("/")])
        if answer.get("status") != "redirect":
            raise ValueError("Gedling's portal didn't open the address's collections")

        _, token, _ = self._get(answer["redirect_url"])
        collections = self._post(answer["redirect_url"], {"_dummy": 1}, token)["data"]
        bins = self.parse_collections(collections)
        bins.sort(key=lambda b: datetime.strptime(b["collectionDate"], date_format))
        return {"bins": bins}

    def _get(self, path):
        """(page HTML, form token, the page's own URL for its actions, or None)."""
        response = self.session.get(BASE_URL + path, timeout=TIMEOUT)
        response.raise_for_status()
        token = re.search(r'"csrf":"([0-9a-f]+)"', response.text)
        if not token:
            raise ValueError("Gedling's portal page has changed: no form token")
        own_url = re.search(r"var AJAX_DYNAMIC_URL =\s*'([^']+)'", response.text)
        return response.text, token.group(1), own_url.group(1) if own_url else None

    def _post(self, path, data, token, stack=()):
        """The JSON the portal answers a page's POST with."""
        storage = {"_global": {"destination_stack": list(stack)}} if stack else {}
        response = self.session.post(
            BASE_URL + path,
            headers={"X-Requested-With": "XMLHttpRequest"},
            data={
                **data,
                "_session_storage": json.dumps(storage),
                "_update_page_content_request": 1,
                "form_check_ajax": token,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    def _open_form(self):
        """The address form, its token and the page's URL for its actions."""
        _, token, own_url = self._get(PAGE)
        if not own_url:
            raise ValueError("Gedling's portal page has changed: no action URL")
        content = self._post(PAGE, {"_dummy": 1}, token)["data"]
        submit = BeautifulSoup(content, "html.parser").find(
            "input", attrs={"name": re.compile(SUBMIT_FIELD)}
        )
        if submit is None:
            raise ValueError("Gedling's bin collections page has changed: no address form")
        return submit.find_parent("form"), token, own_url

    @staticmethod
    def _form_fields(form):
        """The form's own fields (not its buttons) as {name: value}."""
        return {
            i["name"]: i.get("value", "")
            for i in form.find_all("input")
            if i.get("name") and i.get("type") not in ("submit", "button", "checkbox")
        }

    def _search(self, postcode, token, own_url, page_id):
        """[(portal id, "11 Gedling Road Arnold Nottingham NG5 6NQ")] for a postcode."""
        answer = self._post(
            own_url + "&widget_action=fragment_action",
            {
                "code_action": "search",
                "code_params": json.dumps({"search_item": postcode}),
                "fragment_action": "handle_event",
                "fragment_id": ADDRESS_FIELD,
                "fragment_collection_class": "formtable",
                "fragment_collection_editable_values": json.dumps({MANUAL_ADDRESS_FIELD: "0"}),
                "action_cell_id": SEARCH_CELL,
                "action_page_id": page_id,
            },
            token,
        )
        options = (answer.get("response") or {}).get("options") or []
        return [(o["id"], o["summary_address"]) for o in options]

    @staticmethod
    def _choose(addresses, house):
        """The id of the address that starts with the house number or name."""

        def words(text):
            return re.sub(r"[\s,]+", " ", text or "").strip().upper()

        wanted = words(house)
        for address_id, label in addresses:
            if (words(label) + " ").startswith(wanted + " "):
                return address_id
        raise ValueError(
            f"Gedling could not find {house!r} at that postcode. Addresses found: "
            + "; ".join(label for _, label in addresses)
        )

    @staticmethod
    def parse_collections(page_html):
        """[{"type", "collectionDate"}] from the next collections table."""
        bins = []
        for row in BeautifulSoup(page_html, "html.parser").select("table tr"):
            service = row.find(attrs={"data-current_value": True})
            cells = [td.get_text(" ", strip=True) for td in row.find_all("td")]
            if not service or not cells:
                continue
            try:
                day = datetime.strptime(cells[-1], "%a, %d %b %Y")
            except ValueError:
                continue
            # "General Collection Service" -> "General", "Glass Collection Service" -> "Glass"
            name = re.sub(r"\s+Collection Service$", "", service["data-current_value"].strip())
            bins.append({"type": name, "collectionDate": day.strftime(date_format)})
        return bins
