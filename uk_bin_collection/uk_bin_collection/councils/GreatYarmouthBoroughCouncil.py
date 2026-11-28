import json
import re
from datetime import date, datetime

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

FORM_PAGE = (
    "https://myaccount.great-yarmouth.gov.uk/article/6456/Find-my-waste-collection-days"
)
POSTCODE_API = "https://myaccount.great-yarmouth.gov.uk/apiserver/postcode"
FORM_PREFIX = "WASTECOLLECTIONCALENDARV2_ADDRESS"
# The final lookup is slow (about 10s, occasionally much longer).
REQUEST_TIMEOUT_SECONDS = 90

BIN_TYPES = {
    "bulky": "Bulky Collection",
    "green": "Recycling",
    "black": "General Waste",
    "brown": "Garden Waste",
}


def address_for_uprn(addresses: list[dict], uprn: str) -> dict:
    """Return the one address from the postcode lookup with exactly this UPRN."""
    matches = [a for a in addresses if str(a.get("uprn")) == str(uprn).strip()]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one address with UPRN {uprn} in the postcode "
            f"results, found {len(matches)}"
        )
    return matches[0]


def parse_collection_date(text: str, today: date) -> date:
    """Parse "Tuesday  1 December" (no year) to the next such date on or after today.

    The council's weekday has to agree with the date, which picks the year
    and catches a misread date.
    """
    weekday, day_and_month = " ".join(text.split()).split(" ", 1)
    for year in (today.year, today.year + 1):
        parsed = datetime.strptime(f"{day_and_month} {year}", "%d %B %Y").date()
        if parsed >= today and parsed.strftime("%A").lower() == weekday.lower():
            return parsed
    raise ValueError(f"Could not work out the year of collection date '{text}'")


def parse_collections(html: str, today: date) -> dict:
    """Return the next collection of each bin type from the results page."""
    soup = BeautifulSoup(html, "html.parser")
    next_collections: dict[str, dict] = {}
    for area in soup.select(".collection-area"):
        detail = area.select_one(".collection-detail")
        image = area.select_one("img")
        if detail is None or detail.select_one("b") is None:
            continue
        collection_date = parse_collection_date(
            detail.select_one("b").get_text(strip=True), today
        )
        description = detail.get_text(separator=" ", strip=True).lower()
        alt_text = (image.get("alt", "") if image else "").lower()
        for key, name in BIN_TYPES.items():
            if key in alt_text or key in description:
                known = next_collections.get(name)
                if known is None or collection_date < known["date"]:
                    next_collections[name] = {"type": name, "date": collection_date}
                break
    if not next_collections:
        raise ValueError("Could not find any collection dates in the results page")
    return {
        "bins": [
            {"type": c["type"], "collectionDate": c["date"].strftime(date_format)}
            for c in next_collections.values()
        ]
    }


class CouncilClass(AbstractGetBinDataClass):
    """
    Great Yarmouth's bin-day checker is a GOSS iCM form. Cloudflare serves a
    Turnstile "Just a moment" challenge to automated Chrome on the final form
    submission, but not to a session that impersonates Chrome's TLS handshake
    via curl_cffi, so the form is posted over plain HTTP instead of driven in
    a browser. The address fields the page script would fill in after you pick
    an address are taken from the council's own postcode lookup.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
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
        address = address_for_uprn(json.loads(body).get("result") or [], user_uprn)

        fields.update(
            {
                f"{FORM_PREFIX}_ALSF": user_postcode,
                f"{FORM_PREFIX}_ALML": address["uprn"],
                f"{FORM_PREFIX}_UPRN": address["uprn"],
                f"{FORM_PREFIX}_PROPERTY": address["property"],
                f"{FORM_PREFIX}_STREET": address["street"],
                f"{FORM_PREFIX}_AREA": address["line2"],
                f"{FORM_PREFIX}_TOWN": address["town"],
                f"{FORM_PREFIX}_COUNTY": address["county"],
                f"{FORM_PREFIX}_POSTCODE": address["postcode"],
            }
        )
        response = session.post(
            form["action"], data=fields, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return parse_collections(response.text, date.today())
