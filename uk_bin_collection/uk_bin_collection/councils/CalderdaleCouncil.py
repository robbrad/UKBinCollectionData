import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def _match_address(options, uprn=None, paon=None):
    """Match an address option by UPRN or house number/name.
    Returns the UPRN value from the matched option."""
    valid = [(opt["value"], opt.text.strip()) for opt in options if opt.get("value")]
    if not valid:
        raise ValueError("No addresses in dropdown")

    if uprn:
        uprn_str = str(uprn).zfill(12)
        for val, _ in valid:
            if val == uprn_str:
                return val

    if paon:
        paon_norm = str(paon).strip().upper()
        for val, text in valid:
            text_upper = text.upper()
            if text_upper.startswith(paon_norm + " ") or text_upper.startswith(paon_norm + ","):
                return val
        for val, text in valid:
            if paon_norm in text.upper():
                return val

    return valid[0][0]


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)

        base_url = "https://www.calderdale.gov.uk/environment/waste/household-collections/collectiondayfinder.jsp"

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            }
        )

        # Step 1: POST postcode to get address list
        resp = session.post(
            base_url,
            data={
                "postcode": user_postcode,
                "email-address": "",
                "find": "Find an address for this postcode",
            },
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        select_el = soup.find("select", {"id": "uprn"})
        if not select_el:
            raise ValueError(f"No addresses found for postcode: {user_postcode}")

        options = select_el.find_all("option")
        matched_uprn = _match_address(options, uprn=user_uprn, paon=user_paon)

        # Step 2: POST with UPRN to get collection data
        resp = session.post(
            base_url,
            data={
                "postcode": user_postcode,
                "email-address": "",
                "uprn": matched_uprn,
                "gdprTerms": "Yes",
                "privacynoticeid": "323",
                "find": "Show me my collection days",
            },
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"id": "collection"})
        if not table:
            raise ValueError("Collection table not found in response")

        data = {"bins": []}

        for row in table.find_all("tr"):
            bin_info = row.find_all("td")
            if not bin_info:
                continue

            strong = bin_info[0].find("strong")
            if not strong:
                continue
            bin_type = strong.get_text(strip=True)

            for p in bin_info[-1].find_all("p"):
                text = p.get_text(strip=True)
                if "will be your next collection" in text:
                    date_text = text.replace("will be your next collection.", "").strip()
                    date_text = " ".join(date_text.split())
                    try:
                        parsed = datetime.strptime(date_text, "%A %d %B %Y")
                        data["bins"].append(
                            {
                                "type": bin_type,
                                "collectionDate": parsed.strftime(date_format),
                            }
                        )
                    except ValueError:
                        continue

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )
        return data
