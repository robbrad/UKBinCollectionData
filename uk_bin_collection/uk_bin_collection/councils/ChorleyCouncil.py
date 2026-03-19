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
        from bs4 import BeautifulSoup
        import requests
        import re

        postcode = kwargs.get("postcode")
        uprn = kwargs.get("uprn")
        initial_url = "https://forms.chorleysouthribble.gov.uk/xfp/form/71"

        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

        # --- STEP 1: INITIAL LOAD ---
        res = session.get(initial_url)
        soup = BeautifulSoup(res.text, "html.parser")
        token = soup.find("input", {"name": "__token"})["value"]
        page_id = soup.find("input", {"name": "page"})["value"]
        postcode_field = soup.find("input", {"name": re.compile(r".*_0_0")})["name"]
        
        lookup_btn = soup.find("button", {"class": re.compile(r".*btn--lookup.*")})
        lookup_value = lookup_btn["value"] if lookup_btn else ""

        # --- STEP 2: SUBMIT POSTCODE (LOOKUP) ---
        res = session.post(initial_url, data={
            "__token": token,
            "page": page_id,
            "locale": "en_GB",
            postcode_field: postcode,
            "callback": lookup_value 
        })

        # --- STEP 3: SUBMIT UPRN (ADDRESS SELECTION) ---
        soup = BeautifulSoup(res.text, "html.parser")
        token_el = soup.find("input", {"name": "__token"})
        if not token_el:
            raise ValueError("Postcode lookup did not refresh token.")
        
        token = token_el["value"]
        # IMPORTANT: Grab the new page_id from the address selection screen
        page_id = soup.find("input", {"name": "page"})["value"]
        address_el = soup.find("select", {"name": re.compile(r".*_1_0")})
        if not address_el:
            raise ValueError("Address dropdown not found. Postcode step likely failed.")

        # Mimic South Ribble's multi-step logic by sending both postcode and address
        res = session.post(initial_url, data={
            "__token": token,
            "page": page_id,
            "locale": "en_GB",
            postcode_field: postcode,
            address_el["name"]: uprn,
            "next": "Next"
        })

        # --- STEP 4: FINAL SCRAPE ---
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", class_="data-table")
        
        if not table:
            # Check for error messages on the page
            error_msg = soup.find("div", {"class": "alert--error"})
            raise ValueError(f"Final bin table not found. Server said: {error_msg.text.strip() if error_msg else 'Unknown Error'}")

        # Dynamic Mapping from PropertyBins div
        bin_type_map = {}
        prop_bins = soup.find("div", {"id": "PropertyBins"})
        if prop_bins:
            content = prop_bins.get_text().lower()
            mapping_logic = [
                ("blue bin", "Dry Mixed Recycling Collection Service", "Blue bin"),
                ("brown bin", "Paper and Card Collection Service", "Brown bin"),
                ("green bin", "Residual Waste Collection Service", "Green bin"),
                ("grey bin", "Garden Waste Collection Service", "Grey bin"),
                ("black sack", "Residual Waste Sack", "Black Sack"),
                ("food waste", "Food Waste Collection Service", "Food waste caddy")
            ]
            for keyword, service, friendly in mapping_logic:
                if keyword in content:
                    bin_type_map[service] = friendly

        from datetime import datetime
        
        data = {"bins": []}
        for row in table.find("tbody").find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                svc = cells[0].get_text(strip=True)
                # Get "20/03/26"
                date_str = cells[1].get_text(strip=True).split(", ")[-1]
                
                # Convert "20/03/26" (YY) to a real date and back to "20/03/2026" (YYYY)
                try:
                    date_obj = datetime.strptime(date_str, "%d/%m/%y")
                    formatted_date = date_obj.strftime("%d/%m/%Y")
                except ValueError:
                    # Fallback if the site already sent YYYY or a weird format
                    formatted_date = date_str

                data["bins"].append({
                    "type": bin_type_map.get(svc, svc),
                    "collectionDate": formatted_date
                })

        return data