import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        page = f"https://waste.bexley.gov.uk/waste/{user_uprn}"

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        }

        # First request may trigger async page generation; retry if content not ready
        found = False
        for attempt in range(3):
            response = requests.get(page, headers=headers, timeout=30)
            response.raise_for_status()
            if "waste-service-name" in response.text:
                found = True
                break
            time.sleep(3)

        if not found:
            raise ValueError("Bexley WasteWorks page did not return expected content after 3 attempts")

        soup = BeautifulSoup(response.text, features="html.parser")

        data = {"bins": []}

        grids = soup.find_all("div", class_="waste-service-grid")

        for grid in grids:
            h3 = grid.find("h3", class_="waste-service-name")
            if not h3:
                continue

            # Get the main service name (first line of h3, before subtitle)
            service_name_elem = h3.find("span") or h3
            # Extract just the first text node for the bin type
            bin_type = h3.get_text(separator="\n", strip=True).split("\n")[0]

            # Find 'Next collection' in the summary list
            summary_list = grid.find("dl", class_="govuk-summary-list")
            if not summary_list:
                continue

            rows = summary_list.find_all("div", class_="govuk-summary-list__row")
            for row in rows:
                dt = row.find("dt")
                if dt and "Next collection" in dt.get_text():
                    dd = row.find("dd")
                    if not dd:
                        continue

                    next_collection = dd.get_text(strip=True)
                    try:
                        # Parse date like "Wednesday 8 April 2026" or "Tuesday, 8th April 2026"
                        cleaned = remove_ordinal_indicator_from_date_string(next_collection)
                        # Try with comma format first
                        try:
                            parsed_date = datetime.strptime(cleaned, "%A, %d %B %Y")
                        except ValueError:
                            parsed_date = datetime.strptime(cleaned, "%A %d %B %Y")

                        data["bins"].append(
                            {
                                "type": bin_type,
                                "collectionDate": parsed_date.strftime(date_format),
                            }
                        )
                    except ValueError as e:
                        print(f"Error parsing date for {bin_type}: {e}")
                    break

        if not data["bins"]:
            raise ValueError("No collection dates found — page structure may have changed")

        return data
