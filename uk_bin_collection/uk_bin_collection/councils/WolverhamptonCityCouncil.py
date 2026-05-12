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
        paon_norm = str(paon).strip().upper()
        for opt in options:
            label = opt["label"].upper()
            if label.startswith(paon_norm + " ") or label.startswith(paon_norm + ","):
                return opt["uprn"]
        for opt in options:
            label = opt["label"].upper()
            if paon_norm in label:
                return opt["uprn"]

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
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)
        bindata = {"bins": []}

        if not user_uprn and user_postcode:
            user_uprn = _resolve_uprn_from_postcode(user_postcode, user_paon)

        if not user_uprn:
            raise ValueError("Could not resolve address. Provide a postcode or UPRN.")

        user_postcode_encoded = user_postcode.replace(" ", "%20")

        URI = f"https://www.wolverhampton.gov.uk/find-my-nearest/{user_postcode_encoded}/{user_uprn}"

        response = requests.get(URI, timeout=30)

        soup = BeautifulSoup(response.content, "html.parser")

        jumbotron = soup.find("div", class_="jumbotron")
        if not jumbotron:
            raise ValueError("Could not find bin collection data on page")

        for bin_div in jumbotron.select("div.col-md-4"):
            h3 = bin_div.find("h3")
            if not h3:
                continue

            next_date_h4 = bin_div.find(
                "h4", text=lambda x: x and "Next date" in x
            )
            if not next_date_h4:
                continue

            service_name = h3.text.strip()
            next_date = next_date_h4.text.split(": ")[1]

            dict_data = {
                "type": service_name,
                "collectionDate": datetime.strptime(
                    next_date,
                    "%B %d, %Y",
                ).strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
