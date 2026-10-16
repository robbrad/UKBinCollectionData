import re
import time

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

URL = "https://www1.swansea.gov.uk/recyclingsearch/"
HEADERS = {
    "user-agent": "Mozilla/5.0",
}
DATE = re.compile(r"\d{2}/\d{2}/\d{4}")
RETRY_AFTER_SECONDS = 2


def compact(postcode):
    return re.sub(r"\s+", "", postcode or "").upper()


def search(postcode):
    """The result page for a postcode, or None unless its address is in that postcode."""
    session = requests.Session()
    session.headers.update(HEADERS)
    response = session.get(URL, timeout=30)
    response.raise_for_status()
    form = BeautifulSoup(response.text, "html.parser")
    data = {
        field["name"]: field.get("value", "")
        for field in form.select("input[type=hidden]")
        if field.get("name")
    }
    # The road name box is optional; searching by postcode alone is enough
    data.update({"txtRoadName": "", "txtPostCode": postcode, "btnSearch": "Search"})

    response = session.post(URL, data=data, timeout=30)
    response.raise_for_status()
    result = BeautifulSoup(response.text, "html.parser")
    text = re.sub(r"\s+", " ", result.get_text(" "))
    address = re.search(r"Address:\s*(.+?)\s*Collection Day:", text)
    if address and compact(postcode) in compact(address.group(1)):
        return result
    return None


class CouncilClass(AbstractGetBinDataClass):
    """
    Swansea's recycling search is by road and postcode, not by property.
    The UPRN used to be sent as the road name, which the site ignores, so
    only the postcode is used.

    When a search finds nothing, the site can return the previous search's
    result instead (seen October 2026: searching SA1 3SN straight after
    SA4 3PQ returned an address in SA4 3PQ), and a good search straight
    after a failed one can return the failure. So a result is only used if
    its address is in the postcode searched for, with one retry.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)

        result = search(user_postcode)
        if result is None:
            time.sleep(RETRY_AFTER_SECONDS)
            result = search(user_postcode)
        if result is None:
            raise ValueError(f"No collection data found for {user_postcode}")

        bin_data = {"bins": []}
        for label_id, bin_type in (
            ("lblNextRefuse", "Pink Week"),
            ("lblNextRecycling", "Green Week"),
        ):
            label = result.find("span", {"id": label_id})
            match = label and DATE.search(label.get_text())
            if match:
                bin_data["bins"].append(
                    {"type": bin_type, "collectionDate": match.group()}
                )
        return bin_data
