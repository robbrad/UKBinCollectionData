from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        url = "https://www.northyorks.gov.uk/bin-calendar/lookup"
        payload = {
            "selected_address": uprn,
            "submit": "Continue",
            "form_id": "bin_calendar_lookup_form",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.request("POST", url, headers=headers, data=payload)
        bin_data_url = f"{response.url}/ajax"

        response = requests.request("GET", bin_data_url)
        bin_data = response.json()

        # Find the item containing HTML data (the index shifted from 1 to 2)
        html_data = None
        for item in bin_data:
            if isinstance(item, dict) and isinstance(item.get("data"), str) and "<div" in item["data"]:
                html_data = item["data"]
                break

        if not html_data:
            raise ValueError("No HTML bin data found in API response")

        soup = BeautifulSoup(html_data, "html.parser")

        table = (
            soup.find("div", {"id": "upcoming-collection"}).find("table").find("tbody")
        )
        rows = table.find_all("tr")

        data = {"bins": []}

        for row in rows:
            cols = row.find_all("td")
            bin_date = datetime.strptime(cols[0].text.strip(), "%d %B %Y")
            bin_types = [txt for txt in cols[2].stripped_strings]

            for sub_bin in bin_types:
                data["bins"].append(
                    {
                        "type": sub_bin,
                        "collectionDate": bin_date.strftime(date_format),
                    }
                )

        return data
