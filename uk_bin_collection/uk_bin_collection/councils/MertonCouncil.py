# This script pulls (in one hit) the data from Merton Council Bins Data
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# Council class for Merton Council
class CouncilClass(AbstractGetBinDataClass):
    """
    Bin collection scraper for Merton Council.

    This scraper retrieves bin collection schedules from the Merton Council
    FixMyStreet-based website (fixmystreet.merton.gov.uk). The site uses
    JavaScript to dynamically load data, requiring polling until content
    is fully loaded.

    Required Parameters:
        uprn (str): Unique Property Reference Number (numeric only)

    Example:
        >>> council = CouncilClass()
        >>> data = council.run(uprn="4328213")
    """

    # Polling configuration for JavaScript-loaded data
    MAX_POLLING_ATTEMPTS = 10
    POLLING_SLEEP_SECONDS = 2

    def parse_data(self, page: str, **kwargs) -> dict:
        """
        Parse bin collection data from Merton Council's FixMyStreet website.

        The Merton Council website uses JavaScript to dynamically load collection data.
        This method polls the page until the data is fully loaded, then extracts
        bin collection information including type and next collection date.

        Args:
            page (str): Unused - maintained for interface compatibility
            **kwargs: Keyword arguments including:
                - uprn (str): Unique Property Reference Number (numeric only)

        Returns:
            dict: A dictionary containing a list of bins with their collection dates:
                {
                    "bins": [
                        {
                            "type": str,  # Capitalized bin type (e.g., "Food waste")
                            "collectionDate": str  # Formatted date string
                        },
                        ...
                    ]
                }

        Raises:
            ValueError: If uprn is not provided or contains non-numeric characters
            Exception: If timeout occurs waiting for data or if collections div not found

        Note:
            - Skips booking services like "Bulky waste" and "Garden waste"
            - Handles year-boundary dates (e.g., December dates for January collections)
            - Results are sorted by collection date
        """
        uprn = kwargs.get("uprn")
        if not uprn:
            raise ValueError("uprn is required")

        # Validate UPRN format (must be numeric only)
        if not str(uprn).isdigit():
            raise ValueError("uprn must contain only numeric characters")

        # The new Merton site uses JavaScript to load data dynamically.
        # We poll the page until the loading indicator disappears.
        url = f"https://fixmystreet.merton.gov.uk/waste/{uprn}?page_loading=1"
        headers = {
            "x-requested-with": "fetch",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        data = {"bins": []}
        collections = []

        # Poll until data is loaded
        soup = None
        for attempt in range(1, self.MAX_POLLING_ATTEMPTS + 1):
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, features="html.parser")

            # Check if still loading
            if soup.find(id="loading-indicator"):
                if attempt < self.MAX_POLLING_ATTEMPTS:
                    time.sleep(self.POLLING_SLEEP_SECONDS)
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
                                        # Handle year boundary: if parsed date is in the past, assume next year
                                        if collectionDate.date() < datetime.now().date():
                                            collectionDate = collectionDate.replace(year=year + 1)
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
