# This script pulls (in one hit) the data from Merton Council Bins Data
import time

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# Council class for Merton Council
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        if not uprn:
            raise ValueError("uprn is required")

        # The new Merton site uses JavaScript to load data dynamically.
        # We poll the page until the loading indicator disappears.
        url = f"https://fixmystreet.merton.gov.uk/waste/{uprn}?page_loading=1"
        headers = {
            "x-requested-with": "fetch",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        data = {"bins": []}
        collections = []

        # Poll until data is loaded (max 10 attempts)
        max_attempts = 10
        soup = None
        for attempt in range(1, max_attempts + 1):
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, features="html.parser")

            # Check if still loading
            if soup.find(id="loading-indicator"):
                if attempt < max_attempts:
                    time.sleep(2)
                    continue
                else:
                    raise Exception("Timeout waiting for bin collection data to load")
            break

        # Data loaded, parse it
        collections_div = soup.find("div", class_="waste__collections")
        if not collections_div:
            raise Exception("Collections div not found")

        # Find all bin types (h3 elements with waste-service-name class)
        h3s = collections_div.find_all("h3", class_="waste-service-name")

        possible_formats = [
            "%d %B %Y",
            "%A %d %B %Y",
        ]

        # Skip services that are not scheduled collections (booking services)
        skip_services = ["Bulky waste", "Garden waste"]

        for h3 in h3s:
            bin_type = h3.get_text().strip()

            # Skip booking services
            if bin_type in skip_services:
                continue

            # Find parent column containing the summary list
            parent = h3.find_parent("div", class_="govuk-grid-column-two-thirds")
            if parent:
                summary = parent.find("dl", class_="govuk-summary-list")
                if summary:
                    rows = summary.find_all("div", class_="govuk-summary-list__row")
                    for row in rows:
                        key = row.find("dt", class_="govuk-summary-list__key")
                        value = row.find("dd", class_="govuk-summary-list__value")

                        if key and value and "Next collection" in key.get_text():
                            collection_date_str = value.get_text().strip()

                            # Parse the date - format is like "Saturday 15 November"
                            collectionDate = None
                            # Try with day of week
                            date_parts = collection_date_str.split()
                            if len(date_parts) >= 3:
                                # Try parsing with day name, day, month
                                day = date_parts[1]
                                month = date_parts[2]
                                year = datetime.now().year
                                date_str = f"{day} {month} {year}"

                                for format in possible_formats:
                                    try:
                                        collectionDate = datetime.strptime(
                                            date_str, format
                                        )
                                        break
                                    except ValueError:
                                        continue

                            if collectionDate:
                                # Add each collection to the list as a tuple
                                collections.append((bin_type, collectionDate))

        ordered_data = sorted(collections, key=lambda x: x[1])
        for item in ordered_data:
            dict_data = {
                "type": item[0].capitalize(),
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
