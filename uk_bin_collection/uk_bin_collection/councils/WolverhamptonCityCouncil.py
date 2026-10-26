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

    resp = requests.post(AJAX_URL, data=data, headers=headers, cookies=cookies, timeout=30)
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

    if paon:
        # Word-boundary match so "1" doesn't pick "11, ..." or "FLAT 1, 11, ...".
        paon_pattern = re.compile(
            rf"(?<!\w){re.escape(str(paon).strip())}(?!\w)", re.IGNORECASE
        )
        for opt in options:
            if paon_pattern.match(opt["label"]):
                return opt["uprn"]
        for opt in options:
            if paon_pattern.search(opt["label"]):
                return opt["uprn"]
        raise ValueError(
            f"Could not match house number/name '{paon}' among "
            f"{len(options)} addresses for postcode {postcode}"
        )

    return options[0]["uprn"]


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
        bindata = {"bins": []}

        if not user_uprn and user_postcode:
            user_uprn = _resolve_uprn_from_postcode(user_postcode, user_paon)

        if not user_uprn:
            raise ValueError("Could not resolve address. Provide a postcode or UPRN.")

        user_postcode_encoded = user_postcode.replace(" ", "%20")

        URI = f"https://www.wolverhampton.gov.uk/find-my-nearest/{user_postcode_encoded}/{user_uprn}"

        response = requests.get(URI, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        jumbotron = soup.find("div", class_="jumbotron")
        if not jumbotron:
            raise ValueError("Could not find bin collection data on page")

        today = datetime.now().date()

        # Each service is a div.col-md-N (was col-md-4, now col-md-3) holding
        # an <h3> service name and <h4> lines. The date line used to read
        # "Next date: October 27, 2026"; it is now a bare "October 27" with
        # no year, alongside a "Day: Tuesday" line.
        for bin_div in jumbotron.find_all(
            "div", class_=lambda c: c and c.startswith("col-")
        ):
            h3 = bin_div.find("h3")
            if not h3:
                continue

            collection_date = None
            for h4 in bin_div.find_all("h4"):
                text = h4.get_text(strip=True)
                if text.lower().startswith("next date:"):
                    text = text.split(":", 1)[1].strip()
                try:
                    collection_date = datetime.strptime(text, "%B %d, %Y").date()
                    break
                except ValueError:
                    pass
                # No year shown: take the next occurrence on or after today.
                try:
                    collection_date = datetime.strptime(
                        f"{text} {today.year}", "%B %d %Y"
                    ).date()
                except ValueError:
                    continue
                if collection_date < today:
                    collection_date = datetime.strptime(
                        f"{text} {today.year + 1}", "%B %d %Y"
                    ).date()
                break

            if not collection_date:
                continue

            bindata["bins"].append(
                {
                    "type": h3.get_text(strip=True),
                    "collectionDate": collection_date.strftime(date_format),
                }
            )

        if not bindata["bins"]:
            raise ValueError("No bin collection dates found on page")

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
