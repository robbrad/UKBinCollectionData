import json
import re

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

FORM_PAGE = "https://www.swansea.gov.uk/recyclingsearch"
POSTCODE_LOOKUP = "https://www.swansea.gov.uk/apiserver/postcode"
FORM_ID = "RECYCLINGSEARCHMYACCOUNT_FORM"
FIELD = "RECYCLINGSEARCHMYACCOUNT_"
NEXT_TRIGGER = "RECYCLINGSEARCHMYACCOUNT_NEXTBUTTON"

# Swansea collects on a fortnightly pink/green cycle. The names are the
# council's own, and are kept exactly as the previous scraper emitted them
# so existing Home Assistant sensors don't change name.
BIN_TYPES = {"pink": "Pink Week", "green": "Green Week"}

# A full, realistic browser header set (not just User-Agent) - Cloudflare
# scores on header completeness alongside TLS fingerprint and IP reputation.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def _normalise(text: str) -> str:
    """Upper-case with runs of whitespace collapsed, for comparing addresses."""
    return re.sub(r"\s+", " ", (text or "").strip()).upper()


def _compact_postcode(postcode: str) -> str:
    return re.sub(r"\s+", "", (postcode or "")).upper()


def _form_fields(soup: BeautifulSoup):
    """The form's hidden/session fields and the postback URL it submits to."""
    form = soup.find("form", id=FORM_ID)
    if form is None:
        raise ValueError(
            "Could not find the recycling search form on Swansea's page - "
            "the council may have changed or moved it again."
        )
    fields = {
        inp.get("name"): inp.get("value") or ""
        for inp in form.find_all("input")
        if inp.get("name")
    }
    # type="button" controls are not successful form controls, so a real
    # browser never submits the "Find address" button. Posting it back makes
    # the form re-run the lookup step instead of showing the results.
    fields.pop(f"{FIELD}ADDRESSLOOKUPSEARCH", None)
    return fields, form.get("action")


def _addresses(body: str) -> list:
    """The address list from the JSONP postcode lookup."""
    body = body.strip()
    # The lookup is called as JSONP, so the JSON arrives wrapped in a callback.
    match = re.match(r"^[^(]*\((.*)\)[;\s]*$", body, re.DOTALL)
    if match:
        body = match.group(1)
    payload = json.loads(body)
    if "error" in payload:
        raise ValueError(
            payload["error"].get("message", "Postcode lookup failed"),
        )
    addresses = payload.get("result") or []
    # The service reports a bad postcode as a single pseudo-address.
    if len(addresses) == 1 and "Error" in addresses[0]:
        raise ValueError(addresses[0].get("Description", "Invalid postcode"))
    if not addresses:
        raise ValueError("No addresses found for this postcode")
    return addresses


def _select_address(addresses: list, paon: str, uprn: str) -> tuple:
    """Pick the one address the user asked for, or raise.

    Never falls back to "close enough": returning a neighbour's address here
    would mean reporting someone else's collection days as the user's.
    """
    if paon:
        wanted = _normalise(paon)
        # Anchored at the start and on a word boundary, so a house number of
        # "14" matches "14 ORCHARD DRIVE" but not "14A" or "140", and a house
        # name of "LANE COTTAGE" doesn't match "OLD LANE COTTAGE".
        matches = [
            (index, address)
            for index, address in enumerate(addresses)
            if _normalise(address.get("line1")) == wanted
            or _normalise(address.get("line1")).startswith(f"{wanted} ")
        ]
        if not matches:
            raise ValueError(
                f"Could not find house name/number '{paon}' at this postcode. "
                f"Addresses found: "
                f"{', '.join(a.get('line1', '') for a in addresses)}"
            )
        if len(matches) > 1:
            raise ValueError(
                f"House name/number '{paon}' matches more than one address at "
                f"this postcode: "
                f"{', '.join(a.get('line1', '') for _, a in matches)}. "
                f"Please give the full house name or number."
            )
        return matches[0]

    # Backwards compatibility: Swansea used to be configured with a UPRN.
    # The lookup's identifier is a UDPRN for some properties, so this can't
    # be relied on - hence the explicit message rather than a silent miss.
    wanted_uprn = str(uprn).strip()
    for index, address in enumerate(addresses):
        if str(address.get("udprn", "")).strip() == wanted_uprn:
            return index, address
    raise ValueError(
        f"Could not find UPRN '{uprn}' at this postcode. Swansea's new "
        f"collection search looks addresses up by house name/number, so "
        f"please set the house number instead of the UPRN."
    )


def _results_address(soup: BeautifulSoup) -> str:
    """The address the results page says these collections belong to."""
    block = soup.select_one("p.nvp--address .nvp__value")
    return block.get_text(" ", strip=True) if block else ""


def _next_collections(soup: BeautifulSoup) -> list:
    """The "your next collection" date from each of the pink/green cards."""
    collections = []
    for colour, bin_type in BIN_TYPES.items():
        card = soup.select_one(f"article.myaccount-block__collection--{colour}")
        if not card:
            continue
        date = card.select_one("p.myaccount-block__date")
        if not date:
            continue
        try:
            collections.append(
                (
                    datetime.strptime(date.get_text(strip=True), date_format),
                    bin_type,
                )
            )
        except ValueError:
            continue
    return collections


def _calendar_collections(soup: BeautifulSoup) -> list:
    """Every marked day in the twelve month-by-month calendars.

    The cards above only give the next date for each colour; the calendars
    carry a full year, so Home Assistant gets a real schedule rather than
    two dates.
    """
    collections = []
    for table in soup.select("table.bin-calendar"):
        caption = table.caption.get_text(strip=True) if table.caption else ""
        try:
            month = datetime.strptime(caption, "%B %Y")
        except ValueError:
            continue
        for cell in table.select("td"):
            day = cell.get_text(strip=True)
            if not day.isdigit():
                continue
            classes = cell.get("class") or []
            colours = [c for c in BIN_TYPES if f"calendar-{c}" in classes]
            # A day can carry both collections, marked with a single class.
            if "calendar-both" in classes:
                colours = list(BIN_TYPES)
            for colour in colours:
                collections.append((month.replace(day=int(day)), BIN_TYPES[colour]))
    return collections


def _parse_collections(soup: BeautifulSoup) -> list:
    """Collections from the results page, de-duplicated and date-ordered."""
    seen = set(_next_collections(soup)) | set(_calendar_collections(soup))
    return [
        {"type": bin_type, "collectionDate": collection_date.strftime(date_format)}
        for collection_date, bin_type in sorted(seen)
    ]


class CouncilClass(AbstractGetBinDataClass):
    """
    Swansea Council's recycling search is a GOSS iCM form, the same platform
    as Powys's, Gateshead's and Sunderland's - a JSONP postcode lookup plus a
    plain HTTP postback. No Selenium needed.

    The old ASP.NET search at www1.swansea.gov.uk/recyclingsearch/ was
    abandoned (it has returned 502 to everything since at least October 2026)
    when the council moved the service to www.swansea.gov.uk/recyclingsearch.
    The new host is behind a Cloudflare managed challenge keyed on TLS
    fingerprint - a plain requests session gets a 403 "Just a moment..."
    however browser-like its headers are - so the session impersonates
    Chrome's TLS handshake via curl_cffi.

    The results page is only used if its address line is the address that was
    asked for. The old scraper could show a different property's collection
    days when a search found nothing, which is worse than failing.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_paon = kwargs.get("paon")
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        if not user_paon and not user_uprn:
            raise ValueError("A house name/number is required for Swansea")
        check_postcode(user_postcode)

        session = cffi_requests.Session(impersonate="chrome")
        response = session.get(FORM_PAGE, headers=HEADERS, timeout=30)
        response.raise_for_status()
        fields, action = _form_fields(BeautifulSoup(response.text, "html.parser"))

        jsonrpc = {
            "id": 1,
            "method": "postcodeSearch",
            "params": {"provider": "", "postcode": user_postcode},
        }
        response = session.get(
            POSTCODE_LOOKUP,
            params={"jsonrpc": json.dumps(jsonrpc), "callback": "cb"},
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()
        index, address = _select_address(
            _addresses(response.text), user_paon, user_uprn
        )

        # The form's own JavaScript copies the chosen address's parts into
        # these fields and posts the list index back as the select's value.
        fields.update(
            {
                f"{FIELD}ADDRESSLOOKUPPOSTCODE": user_postcode,
                f"{FIELD}ADDRESSLOOKUPADDRESS": str(index),
                f"{FIELD}ADDRESSLINE1": address.get("line1", ""),
                f"{FIELD}ADDRESSLINE2": address.get("line2", ""),
                f"{FIELD}ADDRESSLINE3": address.get("line3", ""),
                f"{FIELD}TOWN": address.get("town", ""),
                f"{FIELD}POSTCODE": address.get("postcode", ""),
                f"{FIELD}UPRN": address.get("udprn", ""),
                f"{FIELD}FORMACTION_NEXT": NEXT_TRIGGER,
            }
        )

        response = session.post(
            action,
            data=fields,
            headers={
                **HEADERS,
                "Referer": FORM_PAGE,
                "Origin": "https://www.swansea.gov.uk",
                "Content-Type": "application/x-www-form-urlencoded",
                "Sec-Fetch-Site": "same-origin",
            },
            timeout=30,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Only trust the page if it is answering about the address we asked
        # for. Swansea has previously answered a failed search with the
        # previous one's result.
        returned = _results_address(soup)
        expected_line1 = _normalise(address.get("line1"))
        if not returned:
            raise ValueError(
                f"Swansea returned no collection details for "
                f"{address.get('line1')}, {address.get('postcode')}."
            )
        if expected_line1 not in _normalise(returned) or _compact_postcode(
            address.get("postcode")
        ) not in _compact_postcode(returned):
            raise ValueError(
                f"Swansea returned collection days for a different address "
                f"({returned}) than the one requested "
                f"({address.get('line1')}, {address.get('postcode')}) - "
                f"refusing to report them."
            )

        bins = _parse_collections(soup)
        if not bins:
            raise ValueError(
                f"No collection dates found for {address.get('line1')}, "
                f"{address.get('postcode')}."
            )
        return {"bins": bins}
