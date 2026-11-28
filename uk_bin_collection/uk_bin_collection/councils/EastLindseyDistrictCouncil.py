import base64
import json
import re
from datetime import datetime

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

FORM_PAGE = "https://www.e-lindsey.gov.uk/mywastecollections"
POSTCODE_API = "https://www.e-lindsey.gov.uk/apiserver/postcode"
REQUEST_TIMEOUT_SECONDS = 30
ADDRESS_LINE_KEYS = (
    "line1",
    "line2",
    "line3",
    "line4",
    "line5",
    "town",
    "county",
    "postcode",
)
SUBMITTED_VARIABLE_SCOPE = "SERVERCLIENTWITHUPDATE"
# The results page embeds its data as base64 JSON; these keys hold the next
# collection date for each bin. Green waste has no "next" date (the council
# only says "every other <day> starting on ..."), so it is not listed.
NEXT_DATE_KEY_TO_BIN_TYPE = {
    "wastenextref": "Refuse (Black Bin)",
    "wastenextrec": "Recycling (Grey Bin)",
    "wastenextpur": "Paper (Purple-Lidded Bin)",
    "wastenextfood": "Food (Orange-Lidded Caddy)",
}


def address_text(address: dict) -> str:
    """Join the address lines the way the council's form shows them."""
    return ", ".join(str(address[key]) for key in ADDRESS_LINE_KEYS if address.get(key))


def select_address(addresses: list[dict], paon: str) -> dict:
    """Return the one address whose text starts with the house number/name.

    The match is anchored at the start and ends on a word boundary, so "1"
    matches "1 Some Road" but not "11 Some Road" or "1A Some Road".
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


def encode_submitted_variables(address: dict) -> str:
    """Build the form's VARIABLES field, which carries the chosen UPRN.

    The council's page script writes these two variables when an address is
    picked and sends them base64-encoded with the postback.
    """
    variables = {
        "ADDRESSSOURCE": {
            "value": address.get("source", ""),
            "scope": SUBMITTED_VARIABLE_SCOPE,
        },
        "ADDRESSUPRN": {"value": address["uprn"], "scope": SUBMITTED_VARIABLE_SCOPE},
    }
    return base64.b64encode(json.dumps(variables).encode()).decode()


def parse_results(html: str) -> dict:
    """Read the next collection dates out of the results page's embedded data."""
    match = re.search(r"Data = JSON\.parse\(helper\.utilDecode\('([^']+)'", html)
    if not match:
        if "Address Out Of Area" in html:
            raise ValueError("The council says this address is out of its area")
        raise ValueError("Could not find the collection data in the results page")
    results = json.loads(base64.b64decode(match.group(1))).get("result") or []
    if not results:
        raise ValueError("The results page held no collection data")
    bins = []
    for key, bin_type in NEXT_DATE_KEY_TO_BIN_TYPE.items():
        date_text = results[0].get(key)
        if not date_text:
            continue
        collection_date = datetime.strptime(
            remove_ordinal_indicator_from_date_string(date_text), "%A %d %B %Y"
        )
        bins.append(
            {"type": bin_type, "collectionDate": collection_date.strftime(date_format)}
        )
    if not bins:
        raise ValueError("Could not find any collection dates in the results page")
    bins.sort(key=lambda b: datetime.strptime(b["collectionDate"], date_format))
    return {"bins": bins}


class CouncilClass(AbstractGetBinDataClass):
    """
    East Lindsey District Council: a GOSS iCM form at e-lindsey.gov.uk/mywastecollections
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
        # The form's names are prefixed with the service year (for example
        # WASTECOLLECTIONDAYS202627OCT), which the council rolls forward, so
        # derive the prefix instead of hardcoding it.
        prefix = next(n for n in fields if n.endswith("_PAGESESSIONID"))[
            : -len("_PAGESESSIONID")
        ]

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

        fields[f"{prefix}_LOOKUP_ADDRESSLOOKUPPOSTCODE"] = user_postcode
        fields[f"{prefix}_LOOKUP_ADDRESSLOOKUPADDRESS"] = str(addresses.index(match))
        fields[f"{prefix}_LOOKUP_CHOSENADDRESS"] = address_text(match)
        fields[f"{prefix}_VARIABLES"] = encode_submitted_variables(match)

        response = session.post(
            form["action"],
            data=fields,
            headers={"Referer": FORM_PAGE},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return parse_results(response.text)
