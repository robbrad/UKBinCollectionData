import re

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

SAT_BASE = "https://satellite.horsham.gov.uk/environment/refuse"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
}


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)

        s = requests.Session()
        s.headers.update(HEADERS)

        r = s.post(
            f"{SAT_BASE}/cal2.asp",
            data={"App": user_postcode, "Submit": "Search"},
            timeout=30,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        select = soup.find("select", {"name": "uprn"})
        if not select:
            raise ValueError(f"No addresses found for postcode {user_postcode}")

        resolved_uprn = None

        if user_uprn:
            uprn_str = str(user_uprn).zfill(12)
            for opt in select.find_all("option"):
                val = (opt.get("value") or "").strip()
                if val == uprn_str:
                    resolved_uprn = val
                    break

        if not resolved_uprn and user_paon:
            paon_lower = user_paon.strip().lower()
            for opt in select.find_all("option"):
                text = opt.get_text(strip=True).lower()
                val = (opt.get("value") or "").strip()
                if val and text.startswith(paon_lower + " "):
                    resolved_uprn = val
                    break
            if not resolved_uprn:
                for opt in select.find_all("option"):
                    text = opt.get_text(strip=True).lower()
                    val = (opt.get("value") or "").strip()
                    if val and paon_lower in text:
                        resolved_uprn = val
                        break

        if not resolved_uprn:
            opts = [o for o in select.find_all("option") if o.get("value", "").strip()]
            if opts:
                resolved_uprn = opts[0].get("value").strip()

        if not resolved_uprn:
            raise ValueError(f"Could not resolve address for {user_postcode}")

        r2 = s.post(
            f"{SAT_BASE}/cal_details.asp",
            data={"uprn": resolved_uprn},
            timeout=30,
        )
        r2.raise_for_status()
        html = r2.text.replace("class='collectionDates' />", "class='collectionDates'>")
        soup2 = BeautifulSoup(html, "html.parser")

        bin_data = {"bins": []}

        table = soup2.find("table", class_="collectionDates")
        if not table:
            table = soup2.find("table")

        if table:
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 3:
                    date_str = cells[1].get_text(strip=True)
                    bin_type = cells[2].get_text(strip=True)
                    if not date_str or not bin_type or date_str.upper() == "DATE":
                        continue
                    try:
                        dt = datetime.strptime(date_str, "%d/%m/%Y")
                        bin_data["bins"].append({
                            "type": bin_type,
                            "collectionDate": dt.strftime(date_format),
                        })
                    except ValueError:
                        continue

        bin_data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bin_data
