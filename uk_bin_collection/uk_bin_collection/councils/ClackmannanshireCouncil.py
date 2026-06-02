import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from icalevents.icalevents import events

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)

        base_url = "https://www.clacks.gov.uk"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        # Step 1: Search by postcode to get address list
        search_url = f"{base_url}/environment/wastecollection/?pc={user_postcode.replace(chr(32), chr(43))}"
        response = requests.get(search_url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=re.compile(r"/environment/wastecollection/id/\d+/"))

        if not links:
            raise ValueError("No addresses found for postcode")

        # Step 2: Find matching address
        address_url = None
        if user_paon:
            for link in links:
                text = link.get_text(strip=True)
                if text.lower().startswith(user_paon.lower()):
                    address_url = base_url + link["href"]
                    break
            if not address_url:
                for link in links:
                    text = link.get_text(strip=True)
                    if user_paon.lower() in text.lower():
                        address_url = base_url + link["href"]
                        break

        if not address_url:
            address_url = base_url + links[0]["href"]

        # Step 3: Get property page and extract iCal URLs
        response = requests.get(address_url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        ics_links = soup.find_all("a", href=re.compile(r"\.ics$"))

        if not ics_links:
            raise ValueError("No iCal files found on property page")

        # Step 4: Parse each iCal file for upcoming events
        now = datetime.now()
        future = now + timedelta(days=60)
        seen = set()

        for ics_link in ics_links:
            ics_url = base_url + ics_link["href"]
            try:
                upcoming = events(ics_url, start=now, end=future)
                for event in sorted(upcoming, key=lambda e: e.start):
                    if event.summary and event.start:
                        bin_type = event.summary.strip()
                        collection_date = event.start.date().strftime(date_format)
                        key = (bin_type, collection_date)
                        if key not in seen:
                            seen.add(key)
                            data["bins"].append(
                                {
                                    "type": bin_type,
                                    "collectionDate": collection_date,
                                }
                            )
            except Exception:
                continue

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
