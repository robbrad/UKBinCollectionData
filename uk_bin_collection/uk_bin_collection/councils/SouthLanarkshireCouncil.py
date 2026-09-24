import re
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

FORM_URL = "https://www.southlanarkshire.gov.uk/xfp/form/831"


class CouncilClass(AbstractGetBinDataClass):
    """
    South Lanarkshire Council's old static "directory_record" bin-day page
    was replaced (#2231) by an interactive XFP form (the same Netcall/
    Firmstep platform used by South Ribble, Oxford, etc.): postcode ->
    address dropdown -> collection schedule. No JavaScript execution is
    needed - it's a plain HTML postback wizard.
    """

    def parse_data(self, page: str, **kwargs: Any) -> Dict[str, List[Dict[str, str]]]:
        user_postcode: Optional[str] = kwargs.get("postcode")
        user_paon: Optional[str] = kwargs.get("paon")
        check_postcode(user_postcode)

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
                )
            }
        )

        # Step 1: load the form and get the CSRF token + postcode field name.
        get_resp = session.get(FORM_URL)
        soup = BeautifulSoup(get_resp.text, "html.parser")

        token = soup.find("input", {"name": "__token"})["value"]
        page_id = soup.find("input", {"name": "page"})["value"]
        postcode_field = soup.find(
            "input", {"type": "text", "name": re.compile(r".*_0_0")}
        )["name"]

        # Step 2: submit the postcode, get back the address dropdown.
        post_resp = session.post(
            FORM_URL,
            data={
                "__token": token,
                "page": page_id,
                "locale": "en_GB",
                postcode_field: user_postcode,
                "next": "Next",
            },
        )
        soup = BeautifulSoup(post_resp.text, "html.parser")

        address_select = soup.find("select", {"name": re.compile(r".*_1_0")})
        if not address_select:
            raise ValueError(
                f"No address dropdown returned for postcode {user_postcode} "
                "- the form may require a different field or have changed again."
            )

        options = [
            (opt.get("value"), opt.get_text(strip=True))
            for opt in address_select.find_all("option")
            if opt.get("value")
        ]
        if not options:
            raise ValueError(f"No addresses found for postcode {user_postcode}")

        chosen_value = None
        if user_paon:
            paon_upper = user_paon.strip().upper()
            for value, text in options:
                if text.upper().startswith(paon_upper):
                    chosen_value = value
                    break
            if not chosen_value:
                raise ValueError(
                    f"Could not match house number/name '{user_paon}' among "
                    f"{len(options)} addresses for postcode {user_postcode}"
                )
        else:
            chosen_value = options[0][0]

        token = soup.find("input", {"name": "__token"})["value"]
        address_field = address_select["name"]

        # Step 3: submit the chosen address, get back the collection schedule.
        final_resp = session.post(
            FORM_URL,
            data={
                "__token": token,
                "page": page_id,
                "locale": "en_GB",
                postcode_field: user_postcode,
                address_field: chosen_value,
                "next": "Next",
            },
        )
        soup = BeautifulSoup(final_resp.text, "html.parser")
        table = soup.find("table", {"id": "bin-table"})
        if not table:
            raise ValueError(
                "Could not find the bin collection table - the form's final "
                "page may have changed again."
            )

        data: Dict[str, List[Dict[str, str]]] = {"bins": []}
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 3:
                # Header row (th cells) or anything else unexpected.
                continue

            type_link = cells[1].find("a")
            bin_type = (
                type_link.get_text(strip=True)
                if type_link
                else cells[1].get_text(strip=True)
            )

            date_text = cells[2].get_text(strip=True)
            try:
                collection_date = datetime.strptime(date_text, date_format)
            except ValueError:
                continue

            data["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": collection_date.strftime(date_format),
                }
            )

        data["bins"].sort(
            key=lambda b: datetime.strptime(b["collectionDate"], date_format)
        )
        return data
