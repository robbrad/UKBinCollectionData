import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        check_paon(user_paon)
        check_postcode(user_postcode)

        url = "https://www.wokingham.gov.uk/rubbish-and-recycling/waste-collection/find-your-bin-collection-day"

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        })

        # Step 1: GET the page to retrieve Drupal form tokens
        r = session.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        form = soup.find("form", id="waste-collection-api-form")
        if not form:
            raise ValueError("Could not find waste collection form on page")

        form_build_id = form.find("input", {"name": "form_build_id"})["value"]
        form_id = form.find("input", {"name": "form_id"})["value"]

        # Step 2: POST postcode to get address list
        data = {
            "postcode_search": user_postcode,
            "form_build_id": form_build_id,
            "form_id": form_id,
            "op": "Find address",
        }
        r2 = session.post(url, data=data, timeout=30)
        r2.raise_for_status()
        soup2 = BeautifulSoup(r2.text, "html.parser")

        # Find the address dropdown
        select = soup2.find("select", id="edit-address-options")
        if not select:
            raise ValueError(f"No addresses found for postcode {user_postcode}")

        options = select.find_all("option")

        # Match by house number (paon)
        target_value = None
        paon_upper = user_paon.upper()
        for opt in options:
            text = opt.text.strip().upper()
            if text.startswith(paon_upper + ",") or text.startswith(paon_upper + " "):
                target_value = opt.get("value")
                break

        if not target_value:
            # Fallback to first real option (skip placeholder)
            for opt in options:
                val = opt.get("value", "")
                if val and val != "0":
                    target_value = val
                    break

        if not target_value:
            raise ValueError(f"Could not match address for {user_paon}, {user_postcode}")

        # Step 3: POST with selected address to get collection dates
        form2 = soup2.find("form", id="waste-collection-api-form")
        form_build_id2 = form2.find("input", {"name": "form_build_id"})["value"]

        data2 = {
            "postcode_search": user_postcode,
            "address_options": target_value,
            "form_build_id": form_build_id2,
            "form_id": form_id,
            "op": "Show collection dates",
        }
        r3 = session.post(url, data=data2, timeout=30)
        r3.raise_for_status()
        soup3 = BeautifulSoup(r3.text, "html.parser")

        # Parse collection cards
        data_out = {"bins": []}
        current_year = datetime.now().year
        cards = soup3.find_all("div", class_="card")

        for card in cards:
            h3 = card.find("h3")
            if not h3:
                continue
            bin_type = h3.get_text(strip=True)

            date_span = card.find("span", class_="card__date")
            if not date_span:
                continue

            date_text = date_span.get_text(strip=True)
            # Date format: "Tuesday 09/06/2026" or "Today 02/06/2026"
            match = re.search(r"(\d{2}/\d{2})(?:/(\d{4}))?", date_text)
            if match:
                day_month = match.group(1)
                year = match.group(2) or str(current_year)
                full_date = f"{day_month}/{year}"
                parsed = datetime.strptime(full_date, "%d/%m/%Y")
                if parsed.date() < datetime.now().date():
                    parsed = parsed.replace(year=current_year + 1)
                data_out["bins"].append({
                    "type": bin_type,
                    "collectionDate": parsed.strftime(date_format),
                })

        return data_out
