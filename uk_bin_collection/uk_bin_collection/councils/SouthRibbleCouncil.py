from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
import requests
import re
from datetime import datetime
from uk_bin_collection.uk_bin_collection.common import check_uprn, check_postcode, date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from dateutil.parser import parse


class CouncilClass(AbstractGetBinDataClass):
    def get_data(self, url: str) -> str:
        # This method is not used in the current implementation
        return ""

    def parse_data(self, page: str, **kwargs: Any) -> Dict[str, List[Dict[str, str]]]:
        postcode: Optional[str] = kwargs.get("postcode")
        uprn: Optional[str] = kwargs.get("uprn")

        if postcode is None or uprn is None:
            raise ValueError("Both postcode and UPRN are required.")

        check_postcode(postcode)
        check_uprn(uprn)

        session = requests.Session()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
            )
        }
        session.headers.update(headers)

        # Step 1: Load form and get token + field names
        initial_url = "https://forms.chorleysouthribble.gov.uk/xfp/form/70"
        get_resp = session.get(initial_url)
        soup = BeautifulSoup(get_resp.text, "html.parser")

        token = soup.find("input", {"name": "__token"})["value"]
        page_id = soup.find("input", {"name": "page"})["value"]
        postcode_field = soup.find("input", {"type": "text", "name": re.compile(".*_0_0")})["name"]

        # Step 2: Submit postcode
        post_resp = session.post(
            initial_url,
            data={
                "__token": token,
                "page": page_id,
                "locale": "en_GB",
                postcode_field: postcode,
                "next": "Next",
            },
        )

        soup = BeautifulSoup(post_resp.text, "html.parser")
        token = soup.find("input", {"name": "__token"})["value"]
        address_field_el = soup.find("select", {"name": re.compile(".*_1_0")})
        if not address_field_el:
            raise ValueError("Failed to find address dropdown after postcode submission.")

        address_field = address_field_el["name"]

        # Step 3: Submit UPRN and retrieve bin data
        final_resp = session.post(
            initial_url,
            data={
                "__token": token,
                "page": page_id,
                "locale": "en_GB",
                postcode_field: postcode,
                address_field: uprn,
                "next": "Next",
            },
        )

        soup = BeautifulSoup(final_resp.text, "html.parser")
        table = soup.find("table", class_="data-table")
        if not table:
            raise ValueError("Could not find bin collection table.")

        rows = table.find("tbody").find_all("tr")
        data: Dict[str, List[Dict[str, str]]] = {"bins": []}

        # Extract bin type mapping from JavaScript
        bin_type_map = {}
        scripts = soup.find_all("script", type="text/javascript")
        for script in scripts:
            if script.string and "const bintype = {" in script.string:
                match = re.search(r'const bintype = \{([^}]+)\}', script.string, re.DOTALL)
                if match:
                    bintype_content = match.group(1)
                    for line in bintype_content.split('\n'):
                        line = line.strip()
                        if '"' in line and ':' in line:
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                key = parts[0].strip().strip('"').strip("'")
                                value = parts[1].strip().rstrip(',').strip().strip('"').strip("'")
                                bin_type_map[key] = value
                    break

        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 2:
                bin_type_cell = cells[0]
                bin_type = bin_type_cell.get_text(strip=True)
                bin_type = bin_type_map.get(bin_type, bin_type)

                date_text = cells[1].get_text(strip=True)
                date_parts = date_text.split(", ")
                date_str = date_parts[1] if len(date_parts) == 2 else date_text

                try:
                    day, month, year = date_str.split('/')
                    year = int(year)
                    if year < 100:
                        year = 2000 + year

                    date_obj = datetime(year, int(month), int(day)).date()

                    data["bins"].append({
                        "type": bin_type,
                        "collectionDate": date_obj.strftime(date_format)
                    })
                except Exception:
                    continue

        return data
