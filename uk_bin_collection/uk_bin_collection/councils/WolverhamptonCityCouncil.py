import re
import time

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

FORM_URL = "https://www.wolverhampton.gov.uk/waste-and-recycling/bin-collection-dates"
AJAX_URL = "https://www.wolverhampton.gov.uk/waste-and-recycling/bin-collection-dates?ajax_form=1&_wrapper_format=drupal_ajax"


def _get_form_build_id():
    """Fetch the Drupal form page and extract form_build_id token."""
    resp = requests.get(FORM_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    build_id_input = soup.find("input", {"name": "form_build_id"})
    if not build_id_input:
        raise ValueError("Could not find form_build_id on Wolverhampton page")
    return build_id_input["value"], resp.cookies


def _resolve_uprn_from_postcode(postcode, paon=None):
    """Use Drupal AJAX form to look up addresses and match by house number."""
    form_build_id, cookies = _get_form_build_id()

    data = {
        "form_build_id": form_build_id,
        "form_id": "cwc_find_my_nearest_search",
        "postcode": postcode,
        "op": "Look up address",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    resp = requests.post(
        AJAX_URL, data=data, headers=headers, cookies=cookies, timeout=30
    )
    resp.raise_for_status()
    ajax_response = resp.json()

    options = []
    for command in ajax_response:
        if command.get("command") == "insert" and command.get("data"):
            soup = BeautifulSoup(command["data"], "html.parser")
            select = soup.find("select", {"name": "uprn"})
            if select:
                for opt in select.find_all("option"):
                    val = opt.get("value", "")
                    if val and val != "_none":
                        options.append({"uprn": val, "label": opt.text.strip()})

    if not options:
        raise ValueError(f"No addresses found for postcode: {postcode}")

    return _match_address(options, paon, postcode)


def _match_address(options, paon, postcode=""):
    """The UPRN of the one address that starts with the house number or name.

    Never guesses: matching a number anywhere in the label, or taking the first
    address when none was given, returns another household's collection days.
    """
    if not paon:
        if len(options) == 1:
            return options[0]["uprn"]
        raise ValueError(
            f"{len(options)} addresses found for postcode {postcode}; "
            "provide a house number or name."
        )

    # Word-boundary match at the start of the label, so "1" doesn't pick
    # "11, ..." or "1A, ...", and "Flat 1" doesn't pick "FLAT 10, ...".
    pattern = re.compile(rf"(?<!\w){re.escape(str(paon).strip())}(?!\w)", re.IGNORECASE)
    matches = [opt for opt in options if pattern.match(opt["label"])]
    if len(matches) == 1:
        return matches[0]["uprn"]
    if matches:
        raise ValueError(
            f"More than one address starts '{paon}' at {postcode}; give more of "
            "the address. Matches: " + "; ".join(opt["label"] for opt in matches)
        )
    raise ValueError(
        f"Could not match house number/name '{paon}' among "
        f"{len(options)} addresses for postcode {postcode}"
    )


def _parse_date(text, today):
    """A collection date with or without a year ("October 27" or "October 27, 2026")."""
    try:
        return datetime.strptime(text, "%B %d, %Y").date()
    except ValueError:
        pass
    # No year shown: take the next occurrence on or after today.
    for year in (today.year, today.year + 1):
        try:
            candidate = datetime.strptime(f"{text} {year}", "%B %d %Y").date()
        except ValueError:
            return None
        if candidate >= today:
            return candidate
    return None


def _parse_collections(html, today):
    """[{"type", "collectionDate"}] from the find-my-nearest results page."""
    soup = BeautifulSoup(html, "html.parser")
    jumbotron = soup.find("div", class_="jumbotron")
    if not jumbotron:
        raise ValueError("Could not find bin collection data on page")

    def is_column(css_class):
        return bool(css_class) and css_class.startswith("col-")

    # Each service is a div.col-md-N (col-md-4 until Oct 2026, now col-md-3)
    # holding an <h3> service name and <h4> lines, one of which is the date
    # ("Next date: October 27, 2026", now a bare "October 27"). Take only the
    # innermost columns: an outer wrapper would repeat its first service.
    bins, seen = [], set()
    for column in jumbotron.find_all("div", class_=is_column):
        if column.find("div", class_=is_column):
            continue
        heading = column.find("h3")
        if not heading:
            continue
        collection_date = None
        for h4 in column.find_all("h4"):
            text = h4.get_text(strip=True)
            if text.lower().startswith("next date:"):
                text = text.split(":", 1)[1].strip()
            collection_date = _parse_date(text, today)
            if collection_date:
                break
        if not collection_date:
            continue
        entry = (heading.get_text(strip=True), collection_date.strftime(date_format))
        if entry not in seen:
            seen.add(entry)
            bins.append({"type": entry[0], "collectionDate": entry[1]})

    if not bins:
        raise ValueError("No bin collection dates found on page")
    bins.sort(key=lambda b: datetime.strptime(b["collectionDate"], date_format))
    return bins


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:

        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon") or kwargs.get("house_number")
        check_postcode(user_postcode)

        if not user_uprn and user_postcode:
            user_uprn = _resolve_uprn_from_postcode(user_postcode, user_paon)

        if not user_uprn:
            raise ValueError("Could not resolve address. Provide a postcode or UPRN.")

        user_postcode_encoded = user_postcode.replace(" ", "%20")

        URI = f"https://www.wolverhampton.gov.uk/find-my-nearest/{user_postcode_encoded}/{user_uprn}"

        response = requests.get(URI, timeout=30)
        response.raise_for_status()

        return {"bins": _parse_collections(response.content, datetime.now().date())}
