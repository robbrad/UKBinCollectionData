import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def _match_address(addresses, uprn=None, paon=None):
    """Match an address from addressfinder results by UPRN or house number/name."""
    if uprn:
        uprn_str = str(uprn).zfill(12)
        for addr in addresses:
            if str(addr.get("UPRN", "")) == uprn_str:
                return addr

    if paon:
        paon_norm = str(paon).strip().upper()
        for addr in addresses:
            label = str(addr.get("label", "")).upper()
            if label.startswith(paon_norm + " ") or label.startswith(paon_norm + ","):
                return addr
        for addr in addresses:
            label = str(addr.get("label", "")).upper()
            if paon_norm in label:
                return addr

    return addresses[0]


def _parse_calendar_page(url):
    """Parse the existing calendar page by UPRN (legacy path)."""
    page = requests.get(url)
    soup = BeautifulSoup(page.text, features="html.parser")

    data = {"bins": []}
    month_class_name = 'class="eventmonth"'
    regular_collection_class_name = "collectiondate regular-collection"
    holiday_collection_class_name = "collectiondate bankholiday-change"
    regex_string = "[^0-9]"

    calendar_collection = soup.find("ol", {"class": "nonumbers news collections"})
    if not calendar_collection:
        return data

    calendar_list = calendar_collection.find_all("li")
    current_month = ""
    current_year = ""

    for element in calendar_list:
        element_tag = str(element)
        if month_class_name in element_tag:
            current_month = datetime.strptime(element.text, "%B %Y").strftime("%m")
            current_year = datetime.strptime(element.text, "%B %Y").strftime("%Y")
        elif regular_collection_class_name in element_tag:
            week_value = element.find_next(
                "span", {"class": f"{regular_collection_class_name}"}
            )
            day_of_week = re.sub(regex_string, "", week_value.text).strip()
            collection_date = datetime(
                int(current_year), int(current_month), int(day_of_week)
            ).strftime(date_format)
            collections = week_value.find_next_siblings("span")
            for item in collections:
                bin_type = item.text.strip()
                if len(bin_type) > 1:
                    data["bins"].append(
                        {"type": bin_type, "collectionDate": collection_date}
                    )
        elif holiday_collection_class_name in element_tag:
            week_value = element.find_next(
                "span", {"class": f"{holiday_collection_class_name}"}
            )
            day_of_week = re.sub(regex_string, "", week_value.text).strip()
            collection_date = datetime(
                int(current_year), int(current_month), int(day_of_week)
            ).strftime(date_format)
            collections = week_value.find_next_siblings("span")
            for item in collections:
                bin_type = item.text.strip()
                if len(bin_type) > 1:
                    data["bins"].append(
                        {
                            "type": bin_type + " (bank holiday replacement)",
                            "collectionDate": collection_date,
                        }
                    )
    return data


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")

        # Postcode path: use addressfinder API to resolve address and get UPRN
        if user_postcode:
            resp = requests.get(
                "https://eastdevon.gov.uk/addressfinder",
                params={"qtype": "bins", "term": user_postcode},
                timeout=30,
            )
            resp.raise_for_status()
            addresses = resp.json()

            if addresses:
                matched = _match_address(addresses, uprn=user_uprn, paon=user_paon)
                user_uprn = matched.get("UPRN")

        if not user_uprn:
            raise ValueError(
                "Could not resolve address. Provide a postcode or UPRN."
            )

        # East Devon requires 12-digit zero-padded UPRNs
        user_uprn = str(user_uprn).zfill(12)
        url = f"https://eastdevon.gov.uk/recycling-and-waste/recycling-waste-information/when-is-my-bin-collected/future-collections-calendar/?UPRN={user_uprn}"

        return _parse_calendar_page(url)
