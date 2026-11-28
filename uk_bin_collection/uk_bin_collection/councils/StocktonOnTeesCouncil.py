import json
import re
from datetime import date, datetime

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

FORM_PAGE = "https://www.stockton.gov.uk/bin-collection-days"
POSTCODE_API = "https://www.stockton.gov.uk/apiserver/postcode"
FORM_PREFIX = "LOOKUPBINDATESBYADDRESSSKIPOUTOFREGIONV2"
REQUEST_TIMEOUT_SECONDS = 30
ADDRESS_LINE_KEYS = (
    "company",
    "department",
    "line1",
    "line2",
    "line3",
    "line4",
    "line5",
    "town",
    "county",
)
LISTED_DATE_FORMAT = "%a %d %B %Y"


def address_text(address: dict) -> str:
    """Join the address lines the way the council's form shows them."""
    return ", ".join(str(address[key]) for key in ADDRESS_LINE_KEYS if address.get(key))


def select_address(addresses: list[dict], paon: str) -> dict:
    """Return the one address whose text starts with the house number/name.

    The match is anchored at the start and ends on a word boundary, so "1"
    matches "1 SOME ROAD" but not "11 SOME ROAD" or "1A SOME ROAD".
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


def _parse_listed_date(text: str, today: date) -> date:
    text = text.strip()
    if text == "Today":
        return today
    return datetime.strptime(
        remove_ordinal_indicator_from_date_string(text), LISTED_DATE_FORMAT
    ).date()


def _next_collection_date(soup: BeautifulSoup, kind: str, today: date) -> date:
    element = soup.find("p", class_=f"myaccount-block__date--{kind}")
    if element is None:
        raise ValueError(f"Could not find the {kind} collection date on the page")
    return _parse_listed_date(element.get_text(), today)


def _garden_collection_date(soup: BeautifulSoup, today: date) -> date | None:
    """Return the next garden date, or None when the service is not running.

    Out of season the council shows the LAST collection of the year in bold
    ("The Garden Waste service has now ended ..."), which must not be reported
    as an upcoming date.
    """
    block = soup.find("div", class_="myaccount-block__item--garden")
    if block is None:
        return None
    emphasised = block.find("strong")
    if emphasised is None:
        return None
    try:
        garden_date = _parse_listed_date(emphasised.get_text(), today)
    except ValueError:
        return None  # e.g. "Date not available"
    return garden_date if garden_date >= today else None


def parse_results(html: str, today: date) -> dict:
    """Convert the council's 'My account' bin blocks to the standard bins dict."""
    soup = BeautifulSoup(html, "html.parser")
    collections = [
        ("Rubbish bin", _next_collection_date(soup, "waste", today)),
        ("Recycling bin", _next_collection_date(soup, "recycling", today)),
    ]
    garden_date = _garden_collection_date(soup, today)
    if garden_date is not None:
        collections.append(("Garden waste bin", garden_date))
    collections.sort(key=lambda collection: collection[1])
    return {
        "bins": [
            {"type": bin_type, "collectionDate": when.strftime(date_format)}
            for bin_type, when in collections
        ]
    }


class CouncilClass(AbstractGetBinDataClass):
    """
    Stockton-on-Tees Borough Council: a GOSS iCM form at stockton.gov.uk/bin-collection-days
    (JSONP postcode lookup, then a plain HTTP postback). Cloudflare serves
    automated Chrome a "Just a moment..." interstitial on the form POST, but not
    a session that impersonates Chrome's TLS handshake via curl_cffi, so no
    browser (or display) is needed.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        check_paon(user_paon)
        check_postcode(user_postcode)

        session = cffi_requests.Session(impersonate="chrome")
        response = session.get(FORM_PAGE, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        form = soup.find("form", action=re.compile("processsubmission"))
        if form is None:
            raise ValueError("Could not find the form on the page")
        button = form.find("button", attrs={"name": re.compile("FORMACTION_NEXT$")})
        fields = {
            field["name"]: field.get("value") or ""
            for field in form.find_all("input", type="hidden")
            if field.get("name")
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
        if not addresses:
            raise ValueError(f"No addresses found for postcode {user_postcode}")
        if len(addresses) == 1 and "Error" in addresses[0]:
            raise ValueError(addresses[0].get("Description", "Invalid postcode"))
        match = select_address(addresses, user_paon)

        # Mirrors what the page script fills in when an address is picked.
        fields[f"{FORM_PREFIX}_ADDRESSLOOKUPPOSTCODE"] = user_postcode
        fields[f"{FORM_PREFIX}_ADDRESSLOOKUPADDRESS"] = str(addresses.index(match))
        fields[f"{FORM_PREFIX}_UPRN"] = str(match["udprn"])
        fields[f"{FORM_PREFIX}_CUSTODIAN"] = str(match.get("custodian") or "")
        fields[f"{FORM_PREFIX}_ADDRESS2"] = match.get("line1") or ""
        fields[f"{FORM_PREFIX}_ADDRESS3"] = match.get("line2") or ""
        fields[f"{FORM_PREFIX}_CITY"] = match.get("town") or ""
        fields[f"{FORM_PREFIX}_POSTCODE"] = match.get("postcode") or ""

        response = session.post(
            form["action"],
            data=fields,
            headers={"Referer": FORM_PAGE},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return parse_results(response.text, date.today())
