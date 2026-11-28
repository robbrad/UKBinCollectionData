import re
from datetime import date, datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from curl_cffi import requests as cffi_requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

FORM_PAGE = "https://www.boston.gov.uk/findwastecollections"
REQUEST_TIMEOUT_SECONDS = 30
POSTCODE_FIELD_SUFFIX = "_COLLECTIONS_SEARCHPOSTCODE"
ADDRESS_FIELD_SUFFIX = "_ADDRESS_ADDRESSUPRN"
NEXT_BUTTON_NAME_SUFFIX = "_FORMACTION_NEXT"


def select_address(options: list[tuple[str, str]], paon: str) -> str:
    """Return the value of the one address option starting with the house name/number.

    `options` are (value, text) pairs. The match is anchored at the start and
    ends on a word boundary, so "7" matches "7 Some Road" but not "17 Some
    Road" or "7A Some Road". Raises ValueError if zero or several options match.
    """
    wanted = re.compile(rf"^{re.escape(paon.strip())}(?!\w)", re.IGNORECASE)
    matches = [
        (value, text)
        for value, text in options
        if value and wanted.match(re.sub(r"\s*,\s*", " ", text.strip()))
    ]
    if len(matches) != 1:
        listed = "; ".join(text for _, text in matches) or "none"
        raise ValueError(
            f"Expected exactly one address starting with '{paon}', "
            f"found {len(matches)}: {listed}"
        )
    return matches[0][0]


def resolve_collection_date(day_text: str, today: date) -> date:
    """Turn 'Thursday 3rd December' into the next matching date on or after today.

    The council omits the year, so try this year and next and keep the one
    whose weekday agrees with the text.
    """
    cleaned = remove_ordinal_indicator_from_date_string(day_text.strip())
    for year in (today.year, today.year + 1):
        try:
            candidate = datetime.strptime(f"{cleaned} {year}", "%A %d %B %Y").date()
        except ValueError:
            continue
        # strptime ignores the weekday, so check it ourselves. The page only
        # shows upcoming dates; tolerate a day of clock skew.
        weekday_agrees = candidate.strftime("%A").lower() == cleaned.split()[0].lower()
        if weekday_agrees and candidate >= today - timedelta(days=1):
            return candidate
    raise ValueError(f"Could not work out a date from '{day_text}'")


def parse_results(html: str, today: date) -> dict:
    """Convert the 'Next: <date>' list items to the standard bins dict."""
    soup = BeautifulSoup(html, "html.parser")
    bins = []
    for item in soup.find_all("div", class_="grid__cell--listitem"):
        title = item.find("h2", class_="item__title")
        content = item.find("div", class_="item__content")
        next_line = content.find("div") if content else None
        if not title or not next_line:
            continue
        day_text = next_line.get_text(" ", strip=True).replace("Next:", "").strip()
        bins.append(
            {
                "type": title.get_text(strip=True),
                "collectionDate": resolve_collection_date(day_text, today).strftime(
                    date_format
                ),
            }
        )
    if not bins:
        raise ValueError("Could not find any collection dates in the results page")
    bins.sort(key=lambda b: datetime.strptime(b["collectionDate"], date_format))
    return {"bins": bins}


def _find_form(soup: BeautifulSoup) -> Tag:
    form = soup.find("form", action=re.compile("processsubmission"))
    if form is None:
        raise ValueError("Could not find the form on the page")
    return form


def _form_fields(form: Tag) -> dict:
    """Hidden state plus any pre-filled text inputs, as the browser would send."""
    return {
        field["name"]: field.get("value") or ""
        for field in form.find_all("input")
        if field.get("name") and field.get("type") in ("hidden", "text")
    }


def _press_next(form: Tag, fields: dict) -> None:
    button = form.find(
        "button", attrs={"name": re.compile(NEXT_BUTTON_NAME_SUFFIX + "$")}
    )
    if button is None:
        raise ValueError("Could not find the Next button on the form")
    fields[button["name"]] = button["value"]


class CouncilClass(AbstractGetBinDataClass):
    """
    Boston Borough Council: a GOSS iCM form at boston.gov.uk/findwastecollections
    driven as plain HTTP postbacks. Cloudflare serves automated Chrome a
    "Just a moment..." interstitial on the first form POST, but not a session
    that impersonates Chrome's TLS handshake via curl_cffi, so no browser is
    needed.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        check_paon(user_paon)
        check_postcode(user_postcode)

        session = cffi_requests.Session(impersonate="chrome")
        response = session.get(FORM_PAGE, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        form = _find_form(BeautifulSoup(response.text, "html.parser"))
        fields = _form_fields(form)
        postcode_field = next(
            name for name in fields if name.endswith(POSTCODE_FIELD_SUFFIX)
        )
        fields[postcode_field] = user_postcode
        _press_next(form, fields)

        response = session.post(
            urljoin(FORM_PAGE, form["action"]),
            data=fields,
            headers={"Referer": FORM_PAGE},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        form = _find_form(BeautifulSoup(response.text, "html.parser"))
        address_select = form.find("select", id=re.compile(ADDRESS_FIELD_SUFFIX + "$"))
        if address_select is None:
            raise ValueError(f"No address list returned for postcode {user_postcode}")
        options = [
            (option.get("value", ""), option.get_text(strip=True))
            for option in address_select.find_all("option")
        ]
        fields = _form_fields(form)
        fields[address_select["name"]] = select_address(options, user_paon)
        _press_next(form, fields)

        response = session.post(
            urljoin(FORM_PAGE, form["action"]),
            data=fields,
            headers={"Referer": FORM_PAGE},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return parse_results(response.text, date.today())
