import json
import re
from datetime import datetime

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

date_format = "%d/%m/%Y"

FORM_PAGE = "https://www.chichester.gov.uk/checkyourbinday"
POSTCODE_API = "https://www.chichester.gov.uk/apiserver/postcode"
FORM_PREFIX = "WASTECOLLECTIONCALENDARV7_CALENDAR"
REQUEST_TIMEOUT_SECONDS = 30
ADDRESS_LINE_KEYS = ("company", "line1", "line2", "line3", "line4", "town", "postcode")


def address_text(address: dict) -> str:
    """Join the address lines the way the council's form shows them."""
    return ", ".join(
        str(address[key])
        for key in ADDRESS_LINE_KEYS
        if address.get(key) not in (None, "")
    )


def select_address(addresses: list[dict], paon: str) -> dict:
    """Return the one address whose text starts with the house number/name.

    The match is anchored at the start and ends on a word boundary, so "7"
    matches "7, Some Road" but not "17, Some Road" or "7A, Some Road".
    Raises ValueError if zero or several addresses match.
    """
    wanted = re.compile(rf"^{re.escape(paon.strip())}(?!\w)", re.IGNORECASE)
    matches = [
        address
        for address in addresses
        if wanted.match(re.sub(r"\s*,\s*", " ", address_text(address)))
    ]
    if len(matches) != 1:
        listed = "; ".join(address_text(address) for address in matches) or "none"
        raise ValueError(
            f"Expected exactly one address starting with '{paon}', "
            f"found {len(matches)}: {listed}"
        )
    return matches[0]


def parse_results(html: str) -> dict:
    """Convert the 'next collection dates' rows to the standard bins dict."""
    soup = BeautifulSoup(html, "html.parser")
    bins = []
    for row in soup.select("div.gi-summary-blocklist__row"):
        key = row.select_one("div.gi-summary-blocklist__key")
        value = row.select_one("div.gi-summary-blocklist__value")
        if not key or not value:
            continue
        date_text = " ".join(value.get_text(" ", strip=True).split())
        bins.append(
            {
                "collectionDate": datetime.strptime(date_text, "%A %d %B %Y").strftime(
                    date_format
                ),
                "type": key.get_text(strip=True),
            }
        )
    if not bins:
        raise ValueError("Could not find any collection dates in the results page")
    bins.sort(key=lambda b: datetime.strptime(b["collectionDate"], date_format))
    return {"bins": bins}


class CouncilClass(AbstractGetBinDataClass):
    """
    Chichester District Council: a GOSS iCM form at chichester.gov.uk/checkyourbinday
    (JSONP postcode lookup, then a plain HTTP postback). Cloudflare serves a
    Turnstile "Just a moment" challenge to automated Chrome but not to a session
    that impersonates Chrome's TLS handshake via curl_cffi, so no browser (or
    display) is needed.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        house_number = kwargs.get("paon") or kwargs.get("number")
        if not house_number:
            raise ValueError(
                "Chichester requires a house number/name via -n / --number"
            )
        check_postcode(user_postcode)

        session = cffi_requests.Session(impersonate="chrome")
        response = session.get(FORM_PAGE, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        form = soup.find("form", action=re.compile("processsubmission"))
        button = form.find("button", attrs={"name": re.compile("FORMACTION_NEXT$")})
        fields = {
            inp["name"]: inp.get("value") or ""
            for inp in form.find_all("input", type="hidden")
            if inp.get("name")
        }
        fields[button["name"]] = button["value"]

        lookup = {
            "id": 1,
            "method": "postcodeSearch",
            "params": {"provider": "", "postcode": user_postcode},
        }
        response = session.get(
            POSTCODE_API,
            params={"jsonrpc": json.dumps(lookup), "callback": "cb"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.text.strip()
        if body.startswith("cb(") and body.endswith(")"):
            body = body[3:-1]
        addresses = json.loads(body).get("result") or []
        match = select_address(addresses, house_number)

        fields[f"{FORM_PREFIX}_ADDRESSLOOKUPPOSTCODE"] = user_postcode
        fields[f"{FORM_PREFIX}_ADDRESSLOOKUPADDRESS"] = str(match["udprn"])
        fields[f"{FORM_PREFIX}_UPRN"] = str(match["uprn"])
        fields[f"{FORM_PREFIX}_ADDRESS"] = address_text(match)

        response = session.post(
            form["action"], data=fields, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return parse_results(response.text)
