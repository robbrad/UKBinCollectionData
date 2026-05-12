import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = str(kwargs.get("uprn")).zfill(12)
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
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

        # Check UPRN exists in dropdown
        options = select_el.find_all("option")
        uprn_values = [opt["value"] for opt in options if opt.get("value")]
        if str(user_uprn) not in uprn_values:
            raise ValueError(
                f"UPRN {user_uprn} not found for postcode {user_postcode}. "
                f"Available: {uprn_values[:5]}"
            )

        # Step 2: POST with UPRN to get collection data
        resp = session.post(
            base_url,
            data={
                "postcode": user_postcode,
                "email-address": "",
                "uprn": str(user_uprn),
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

            # Find next collection date in the last column
            for p in bin_info[-1].find_all("p"):
                text = p.get_text(strip=True)
                if "will be your next collection" in text:
                    date_text = text.replace("will be your next collection.", "").strip()
                    # Normalise whitespace (server pads with spaces)
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
