import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        """
        Extracts bin types and their next collection dates for a given UPRN from Sutton Council's waste page.

        Parameters:
            uprn (str): Unique Property Reference Number used to construct the council URL to fetch bin information.

        Returns:
            dict: A dictionary with a "bins" key containing a list of dictionaries. Each entry has:
                - "type" (str): Human-readable bin/service name.
                - "collectionDate" (str): Next collection date formatted as "DD/MM/YYYY".
                The list is sorted by collection date in ascending order.

        Raises:
            RuntimeError: If the council page still reports "Loading your bin days..." after polite retries.
        """
        user_uprn = kwargs.get("uprn")
        data = {"bins": []}

        URI = f"https://waste-services.sutton.gov.uk/waste/{user_uprn}"

        # --- Session with polite retry policy
        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": "uk-bin-collection/1.0 (+https://github.com/robbrad/UKBinCollectionData)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Connection": "close",
            }
        )
        retry = Retry(
            total=5,
            backoff_factor=1.5,  # 0, 1.5s, 3s, 4.5s, 6s...
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=True,
        )
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.mount("http://", HTTPAdapter(max_retries=retry))

        # --- Initial fetch with timeout
        r = s.get(URI, timeout=20)
        # If 429 and Retry-After present, requests+urllib3 will already honor it.
        r.raise_for_status()

        # --- Poll only if the page explicitly says it's still loading
        # Use exponential backoff and a hard cap to avoid rate limits
        max_polls = 5  # don't keep hammering
        delay = 2.0
        poll = 0
        while "Loading your bin days..." in r.text and poll < max_polls:
            time.sleep(delay)
            delay = min(delay * 2, 30)  # grow delay but cap it
            r = s.get(URI, timeout=20)
            if r.status_code == 429:
                # manual respect if upstream Retry didn’t catch (e.g., no header)
                retry_after = int(r.headers.get("Retry-After", "10"))
                time.sleep(min(retry_after, 60))
            r.raise_for_status()
            poll += 1

        if "Loading your bin days..." in r.text:
            # fail fast with a clear message so callers can back off scheduling
            raise RuntimeError(
                "Sutton page still loading after polite retries; back off and try later."
            )

        soup = BeautifulSoup(r.content, "html.parser")
        print(soup)
        current_year = datetime.now().year

        waste_services = soup.find_all("div", class_="waste-service-grid")

        for service in waste_services:
            waste_service_name = service.find(
                "h3", class_="govuk-heading-m waste-service-name"
            )
            service_title = waste_service_name.get_text(strip=True)
            list_row = service.find_all("div", class_="govuk-summary-list__row")
            for row in list_row:
                next_collection = row.find("dt", string="Next collection")

                if next_collection:
                    next_collection_date = next_collection.find_next_sibling().get_text(
                        strip=True
                    )
                    # Extract date part and remove the suffix
                    next_collection_date_parse = next_collection_date.split(",")[
                        1
                    ].strip()
                    day, month = next_collection_date_parse.split()[:2]

                    day = remove_ordinal_indicator_from_date_string(day)

                    # Reconstruct the date string without the suffix
                    date_without_suffix = f"{day} {month}"

                    # Parse the date string to a datetime object
                    date_object = datetime.strptime(date_without_suffix, "%d %B")

                    # Get the current year
                    current_year = datetime.now().year

                    # Append the year to the date
                    date_with_year = date_object.replace(year=current_year)

                    # Check if the parsed date is in the past compared to the current date
                    if date_object < datetime.now():
                        # If the parsed date is in the past, assume it's for the next year
                        current_year += 1

                    # Format the date with the year
                    date_with_year_formatted = date_with_year.strftime(
                        "%d/%m/%Y"
                    )  # Format the date as '%d/%m/%Y'

                    # Create the dictionary with the formatted data
                    dict_data = {
                        "type": service_title,
                        "collectionDate": date_with_year_formatted,
                    }
                    data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], "%d/%m/%Y")
        )
        return data
