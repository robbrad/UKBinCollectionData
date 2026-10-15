import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import check_postcode, date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

FORM_URL = "https://www.hillingdon.gov.uk/collection-day"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _choose_address(
    options: List[Tuple[str, str]], paon: Optional[str], uprn: Optional[str]
) -> str:
    """Match by UPRN, else by address text.

    Older configs hold the full address in the previous form's style
    ("1, Milverton Drive, Ickenham, UB10 8PP, Ickenham, Hillingdon"), newer
    ones may hold just the house number, so accept either.
    """
    if uprn:
        for value, _ in options:
            if value == str(uprn).strip():
                return value
    if paon:
        wanted = _normalise(paon)
        for value, text in options:
            option = _normalise(text)
            if wanted == option or wanted.startswith(option + " "):
                return value
        for value, text in options:
            if _normalise(text).startswith(wanted + " "):
                return value
    raise ValueError(
        f"Could not match address '{paon or uprn}' among {len(options)} addresses"
    )


def _field_value(soup: BeautifulSoup, label: str) -> str:
    for tag in soup.find_all("label"):
        if tag.get_text(strip=True) == label and tag.get("for"):
            field = soup.find(id=tag["for"])
            if field is not None:
                return field.get("value", "").replace("\\n", "").strip().strip('"')
    raise ValueError(f"Could not find '{label}' on the results page")


def _parse_results(html: str) -> Dict[str, List[Dict[str, str]]]:
    soup = BeautifulSoup(html, "html.parser")
    date_text = _field_value(soup, "Date")  # e.g. "Tuesday 20-10-2026"
    collection_date = datetime.strptime(date_text.split()[-1], "%d-%m-%Y")
    types = [t.strip() for t in _field_value(soup, "Types of containers").split(",")]
    return {
        "bins": [
            {"type": t, "collectionDate": collection_date.strftime(date_format)}
            for t in types
            if t
        ]
    }


class CouncilClass(AbstractGetBinDataClass):
    """
    Hillingdon's lookup is a Jadu XFP form: enter a postcode, press Lookup to
    get an address list, choose an address and press Next to see the next
    collection date and which containers are due.
    """

    def parse_data(self, page: str, **kwargs: Any) -> Dict[str, Any]:
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        user_uprn = kwargs.get("uprn")
        check_postcode(user_postcode)
        if not user_paon and not user_uprn:
            raise ValueError("Provide a house number/address or a UPRN")

        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        resp = session.get(FORM_URL, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find("form", action=re.compile(r"/xfp/form/"))
        if form is None:
            raise ValueError("Could not find the collection day form")
        action = urljoin(resp.url, form["action"])
        postcode_field = form.find("input", autocomplete="postal-code")["name"]
        lookup = form.find("button", class_="btn--lookup")

        def fields(f) -> Dict[str, str]:
            return {
                "__token": f.find("input", {"name": "__token"})["value"],
                "page": f.find("input", {"name": "page"})["value"],
                "locale": "en_GB",
                postcode_field: user_postcode,
            }

        resp = session.post(
            action,
            data={**fields(form), "callback": lookup["value"]},
            timeout=30,
        )
        resp.raise_for_status()
        form = BeautifulSoup(resp.text, "html.parser").find(
            "form", action=re.compile(r"/xfp/form/")
        )
        select = form.find("select", {"name": re.compile(r"_1_0$")}) if form else None
        options = [
            (o["value"], o.get_text(strip=True))
            for o in (select.find_all("option") if select else [])
            if o.get("value")
        ]
        if not options:
            raise ValueError(f"No addresses found for postcode {user_postcode}")

        resp = session.post(
            action,
            data={
                **fields(form),
                select["name"]: _choose_address(options, user_paon, user_uprn),
                "next": "Next",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return _parse_results(resp.text)
