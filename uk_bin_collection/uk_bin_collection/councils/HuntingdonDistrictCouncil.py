#!/usr/bin/env python3
"""
Huntingdonshire District Council bin collection scraper.

Scrapes bin collection data from the Huntingdonshire District Council website.
Supports domestic waste, dry recycling, garden waste, and food waste collections.
"""
import re
from datetime import datetime

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Scraper for Huntingdonshire District Council bin collections.

    Parses the council's refuse calendar page to extract collection dates
    for domestic waste, dry recycling, garden waste, and food waste bins.
    """

    def parse_data(self, page, **kwargs) -> dict:
        """
        Parse bin collection data from Huntingdonshire District Council.

        Args:
            page: Unused (maintained for interface compatibility).
            **kwargs: Must contain 'uprn' (Unique Property Reference Number).

        Returns:
            dict: Dictionary with 'bins' key containing list of bin types and dates.

        Raises:
            ValueError: If UPRN is invalid or page cannot be fetched/parsed.
        """
        user_uprn = kwargs.get("uprn")
        url_fallback = kwargs.get("url")

        # Validate UPRN if provided
        if user_uprn:
            check_uprn(user_uprn)
            url = f"https://www.huntingdonshire.gov.uk/refuse-calendar/{user_uprn}"
        elif url_fallback:
            # Fallback for legacy URL storage. Ensures backwards compatibility.
            url = url_fallback
        else:
            raise ValueError(
                "Missing or invalid UPRN and no URL provided. "
                "Please supply a valid 'uprn' or 'url' parameter."
            )

        try:
            page = requests.get(url, timeout=30)
            page.raise_for_status()
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch bin data: {str(e)}")

        soup = BeautifulSoup(page.text, "html.parser")

        data = {"bins": []}

        results_container = soup.find("ul", class_="d-print-none")
        if not results_container:
            raise ValueError("Could not find bin collection data on page")
        results = results_container.find_all("li")

        for result in results:
            # Skip items without a date (e.g., "does not receive X collection" messages)
            # These will have a <strong> tag with the date once the service is active
            strong_tag = result.find("strong")
            if not strong_tag:
                continue

            # Extract bin type from text
            # Pattern 1: "...for your domestic waste in your..." / "...for your dry recycling waste in your..."
            # Pattern 2: "Your next weekly food collection is on..."
            text = result.get_text(strip=True)
            type_match = re.search(r"your (.+?) (?:waste )?in your", text)
            if type_match:
                bin_type = type_match.group(1).capitalize()
                if "waste" not in bin_type.lower():
                    bin_type += " waste"
            elif "food collection" in text.lower():
                bin_type = "Food waste"
            else:
                raise ValueError(
                    f"Failed to parse bin type from text: '{text}'. "
                    "The page format may have changed."
                )

            date_text = strong_tag.get_text(strip=True)
            try:
                collection_date = datetime.strptime(
                    date_text, "%A %d %B %Y"
                ).strftime(date_format)
            except ValueError as e:
                raise ValueError(
                    f"Failed to parse collection date '{date_text}' with format '%A %d %B %Y'. "
                    f"The page format may have changed. Original error: {e}"
                )

            data["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": collection_date,
                }
            )

        return data
