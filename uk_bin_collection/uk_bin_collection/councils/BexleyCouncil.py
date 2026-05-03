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

        page = f"https://waste.bexley.gov.uk/waste/{user_uprn}"

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        }

        session = requests.Session()
        session.headers.update(headers)

        # Initial request triggers server-side schedule computation and sets session cookie
        session.get(page, timeout=60)

        # Poll for results — server computes async, JS client polls ?page_loading=1
        # with x-requested-with header to get the content fragment
        response = None
        for attempt in range(30):
            response = session.get(
                f"{page}?page_loading=1",
                headers={"x-requested-with": "fetch"},
                timeout=60,
            )
            response.raise_for_status()
            if "waste-service-name" in response.text:
                break
            time.sleep(2)

        soup = BeautifulSoup(response.text, features="html.parser")

        data = {"bins": []}

        grids = soup.find_all("div", class_="waste-service-grid")

        for grid in grids:
            h3 = grid.find("h3", class_="waste-service-name")
            if not h3:
                continue

            bin_type = h3.get_text(separator="\n", strip=True).split("\n")[0]

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
                        if "collected today" in next_collection.lower() or "could not be collected today" in next_collection.lower():
                            parsed_date = datetime.now()
                        else:
                            cleaned = remove_ordinal_indicator_from_date_string(next_collection)
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

        return data
