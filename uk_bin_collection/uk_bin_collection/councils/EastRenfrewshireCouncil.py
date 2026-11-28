import re
from datetime import datetime

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

FORM_PAGE = "https://eastrenfrewshire.gov.uk/bin-days"
REQUEST_TIMEOUT_SECONDS = 30
COUNCIL_DATE_FORMAT = "%d/%m/%Y"


def parse_form(html: str) -> tuple[str, dict, str]:
    """Return (action URL, hidden fields, submit-button field name) of the wizard form.

    The submit button's name is sent with its value, exactly as a browser would.
    """
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form", action=re.compile("processsubmission"))
    if form is None:
        raise ValueError("Could not find the bin day form in the page")
    fields = {
        inp["name"]: inp.get("value") or ""
        for inp in form.find_all("input", type="hidden")
        if inp.get("name")
    }
    button = form.find("button", attrs={"name": re.compile("FORMACTION_NEXT$")})
    if button is None:
        raise ValueError("Could not find the submit button in the bin day form")
    fields[button["name"]] = button["value"]
    return form["action"], fields, button["name"]


def parse_address_options(html: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (select field name, [(address text, UPRN), ...]) from the address page."""
    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", id=re.compile("UPRN$"))
    if select is None:
        raise ValueError("No address list in the page: is the postcode valid?")
    options = [
        (option.get_text(" ", strip=True), option["value"])
        for option in select.find_all("option")
        if option.get("value")
    ]
    if not options:
        raise ValueError("The council found no addresses for this postcode")
    return select["name"], options


def select_address(
    options: list[tuple[str, str]], paon: str | None, uprn: str | None
) -> str:
    """Return the UPRN value of the one address matching the UPRN or house number.

    A house number must match at the start of the address as a whole word
    ("23" matches "23 Woodvale Avenue", not "123 ..." or "23A ..."). Raises
    ValueError if nothing, or more than one address, matches.
    """
    if uprn:
        matches = [
            (text, value)
            for text, value in options
            if value.lstrip("0") == str(uprn).strip().lstrip("0")
        ]
        wanted = f"UPRN {uprn}"
    elif paon:
        pattern = re.compile(rf"^{re.escape(paon.strip())}(?!\w)", re.IGNORECASE)
        matches = [(text, value) for text, value in options if pattern.match(text)]
        wanted = f"house number/name '{paon}'"
    else:
        raise ValueError("Provide a house number (-n) or a UPRN (-u)")
    if len(matches) != 1:
        listed = "; ".join(text for text, _ in matches) or "none"
        raise ValueError(
            f"Expected exactly one address for {wanted}, "
            f"found {len(matches)}: {listed}"
        )
    return matches[0][1]


def parse_results(html: str) -> dict:
    """Convert the results table (Date, Day, Bin Type) to the standard bins dict."""
    soup = BeautifulSoup(html, "html.parser")
    header = soup.find("th", string="Bin Type")
    if header is None:
        raise ValueError("Could not find the collection results table in the page")
    bins = []
    for row in header.find_parent("table").find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) < 3 or not cells[0].get_text(strip=True):
            continue
        collection_date = cells[0].get_text(strip=True)
        datetime.strptime(collection_date, COUNCIL_DATE_FORMAT)
        for line in cells[2].get_text(separator="\n").split("\n"):
            if line.strip():
                bins.append({"type": line.strip(), "collectionDate": collection_date})
    if not bins:
        raise ValueError("The collection results table was empty")
    bins.sort(key=lambda b: datetime.strptime(b["collectionDate"], COUNCIL_DATE_FORMAT))
    return {"bins": bins}


class CouncilClass(AbstractGetBinDataClass):
    """
    East Renfrewshire's bin-day checker is a GOSS iCM form: a plain HTTP
    postback wizard (postcode -> address list -> results). Cloudflare
    serves a Turnstile "Just a moment" challenge to automated Chrome but
    not to a session that impersonates Chrome's TLS handshake via curl_cffi,
    so no browser is needed.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        user_uprn = kwargs.get("uprn")
        check_postcode(user_postcode)

        session = cffi_requests.Session(impersonate="chrome")
        response = session.get(FORM_PAGE, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        action, fields, _ = parse_form(response.text)
        fields[self._input_name(response.text, "postal-code")] = user_postcode

        response = session.post(action, data=fields, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        action, fields, _ = parse_form(response.text)
        select_name, options = parse_address_options(response.text)
        fields[select_name] = select_address(options, user_paon, user_uprn)

        response = session.post(action, data=fields, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return parse_results(response.text)

    @staticmethod
    def _input_name(html: str, autocomplete: str) -> str:
        """Name of the text input with the given autocomplete hint (the postcode box)."""
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form", action=re.compile("processsubmission"))
        field = form.find("input", attrs={"autocomplete": autocomplete})
        if field is None:
            raise ValueError("Could not find the postcode field in the form")
        return field["name"]
