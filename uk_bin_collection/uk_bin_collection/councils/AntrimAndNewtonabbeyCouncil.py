import re

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BIN_CHECKER_URL = "https://antrimandnewtownabbey.gov.uk/binchecker/"
SCHEDULE_URL = (
    "https://antrimandnewtownabbey.gov.uk/residents/bins-recycling/bins-schedule/?Id={}"
)
LOOKUP_PREFIX = "p$lt$ctl07$pageplaceholder$p$lt$ctl02$BinCollectionLookup$"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    ),
}


def match_address(options, paon):
    """Pick the option whose label starts with (or contains) the house number/name.

    options: list of (value, label). Prefers "<paon> <street>" over "<paon> <flat>",
    then any whole-word occurrence. Raises ValueError if nothing matches.
    """
    paon = str(paon).strip()
    p = re.escape(paon)
    for pattern in (rf"^{p}[\s,]+[A-Za-z]", rf"^{p}[\s,]", rf"(^|[\s,]){p}([\s,]|$)"):
        for value, label in options:
            if re.search(pattern, label.strip(), re.I):
                return value
    raise ValueError(f"No address matching '{paon}' found for this postcode")


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def find_property_id(self, session, postcode, paon):
        """Search the council bin checker by postcode and return its property Id."""
        response = session.get(BIN_CHECKER_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        form_data = {
            i["name"]: i.get("value", "")
            for i in soup.select("form#form input[type=hidden]")
            if i.get("name")
        }
        form_data[LOOKUP_PREFIX + "txtBinSearch"] = postcode
        form_data[LOOKUP_PREFIX + "btnBinSearch"] = "Go"

        response = session.post(BIN_CHECKER_URL, data=form_data, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        dropdown = soup.find("select", {"name": LOOKUP_PREFIX + "ddlAddress"})
        if not dropdown:
            raise ValueError(f"No addresses found for postcode {postcode}")
        options = [
            (o.get("value"), o.get_text(strip=True))
            for o in dropdown.find_all("option")
            if o.get("value")
        ]
        return match_address(options, paon)

    def parse_data(self, page: str, **kwargs) -> dict:

        bindata = {"bins": []}

        # Postcode + house number: look up the council's own property Id
        # (not a UPRN) instead of relying on a hand-copied ?Id= URL.
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon") or kwargs.get("house_number")
        if user_postcode and user_paon:
            session = requests.Session()
            session.headers.update(HEADERS)
            property_id = self.find_property_id(session, user_postcode, user_paon)
            response = session.get(SCHEDULE_URL.format(property_id), timeout=30)
            response.raise_for_status()
            content = response.content
        else:
            content = page.content

        soup = BeautifulSoup(content, "html.parser")

        collection_divs = soup.select("div.feature-box.bins")
        if not collection_divs:
            raise Exception("No collections found")

        for collection_div in collection_divs:
            date_p = collection_div.select_one("p.date")
            if not date_p:
                continue

            # Thu 22 Aug, 2024
            date_ = datetime.strptime(date_p.text.strip(), "%a %d %b, %Y").strftime(
                "%d/%m/%Y"
            )
            bins = collection_div.select("li")
            if not bins:
                continue
            for bin in bins:
                if not bin.text.strip():
                    continue
                bin_type = bin.text.strip()

                dict_data = {
                    "type": bin_type,
                    "collectionDate": date_,
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
