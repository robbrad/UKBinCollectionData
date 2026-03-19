from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime
from typing import Any, Dict, List

from uk_bin_collection.uk_bin_collection.common import check_uprn, check_postcode
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs: Any) -> Dict[str, List[Dict[str, str]]]:
        # Validate upfront (Bot Requirement)
        user_postcode = kwargs.get("postcode")
        user_uprn = kwargs.get("uprn")
        check_postcode(user_postcode)
        check_uprn(user_uprn)

        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        initial_url = kwargs.get("url", "https://forms.chorleysouthribble.gov.uk/xfp/form/71")

        # --- STEP 1: INITIAL LOAD ---
        res = session.get(initial_url, timeout=30)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        
        token_el = soup.find("input", {"name": "__token"})
        if not token_el:
            raise ValueError("Could not find __token field on initial page.")
        token = token_el["value"]

        page_id_el = soup.find("input", {"name": "page"})
        if not page_id_el:
            raise ValueError("Could not find page ID field on initial page.")
        page_id = page_id_el["value"]

        postcode_el = soup.find("input", {"name": re.compile(r".*_0_0")})
        if not postcode_el:
            raise ValueError("Could not find postcode input field.")
        postcode_field = postcode_el["name"]
        
        lookup_btn = soup.find("button", {"class": re.compile(r".*btn--lookup.*")})
        lookup_value = lookup_btn["value"] if lookup_btn else ""

        # --- STEP 2: SUBMIT POSTCODE ---
        res = session.post(initial_url, data={
            "__token": token,
            "page": page_id,
            "locale": "en_GB",
            postcode_field: user_postcode,
            "callback": lookup_value 
        }, timeout=30)
        res.raise_for_status()

        # --- STEP 3: SUBMIT UPRN ---
        soup = BeautifulSoup(res.text, "html.parser")
        token_el = soup.find("input", {"name": "__token"})
        if not token_el:
            raise ValueError("Postcode lookup did not refresh token. Check postcode validity.")
        token = token_el["value"]
        
        page_id_el = soup.find("input", {"name": "page"})
        if not page_id_el:
            raise ValueError("Could not find page ID field on address selection page.")
        page_id = page_id_el["value"]
        
        address_el = soup.find("select", {"name": re.compile(r".*_1_0")})
        if not address_el:
            raise ValueError("Address dropdown not found. Postcode step likely failed.")

        res = session.post(initial_url, data={
            "__token": token,
            "page": page_id,
            "locale": "en_GB",
            postcode_field: user_postcode,
            address_el["name"]: user_uprn,
            "next": "Next"
        }, timeout=30)
        res.raise_for_status()

        # --- STEP 4: SCRAPE DATA & DECODE SCRIPT ---
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", class_="data-table")
        
        if not table:
            error_msg = soup.find("div", {"class": "alert--error"})
            raise ValueError(f"Final bin table not found. Server said: {error_msg.text.strip() if error_msg else 'Unknown Error'}")

        # Extract the bin mapping exactly from the embedded script
        bin_type_map = {}
        for script in soup.find_all("script"):
            if script.string:
                # Find lines like: bintype["Service Name"] = "Friendly Name";
                matches = re.findall(r'bintype\[["\']([^"\']+)["\']\]\s*=\s*["\']([^"\']+)["\']', script.string)
                for service, friendly in matches:
                    bin_type_map[service] = friendly

                # Also catch the static dictionary style (South Ribble style) just in case they revert
                static_match = re.search(r'const bintype = \{([^}]+)\}', script.string, re.DOTALL)
                if static_match:
                    for line in static_match.group(1).split('\n'):
                        if ':' in line and '"' in line:
                            parts = line.split(':', 1)
                            key = parts[0].strip().strip('"').strip("'")
                            val = parts[1].strip().rstrip(',').strip().strip('"').strip("'")
                            if key and val:
                                bin_type_map[key] = val

        data = {"bins": []}
        for row in table.find("tbody").find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                svc = cells[0].get_text(strip=True)
                date_str = cells[1].get_text(strip=True).split(", ")[-1]
                
                try:
                    date_obj = datetime.strptime(date_str, "%d/%m/%y")
                    formatted_date = date_obj.strftime("%d/%m/%Y")
                except ValueError as e:
                    raise ValueError(f"Unable to parse date format from string: '{date_str}'") from e

                data["bins"].append({
                    "type": bin_type_map.get(svc, svc),
                    "collectionDate": formatted_date
                })

        return data
