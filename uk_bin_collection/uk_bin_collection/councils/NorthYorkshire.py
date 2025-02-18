from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        # Figure bin data URL from UPRN
        url = "https://www.northyorks.gov.uk/bin-calendar/lookup"
        payload = {
            "selected_address": uprn,
            "submit": "Continue",
            "form_id": "bin_calendar_lookup_form",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        # This endpoint redirects to the data url.
        response = requests.request("POST", url, headers=headers, data=payload)
        bin_data_url = f"{response.url}/ajax"

        # Get bin data
        response = requests.request("GET", bin_data_url)
        bin_data = response.json()

        # Parse bin data
        soup = BeautifulSoup(bin_data[1]["data"], "html.parser")

        # All collection info is in the table
        table = (
            soup.find("div", {"id": "upcoming-collection"}).find("table").find("tbody")
        )
        rows = table.find_all("tr")

        data = {"bins": []}

        for row in rows:
            cols = row.find_all("td")
            # First column is date
            bin_date = datetime.strptime(cols[0].text.strip(), "%d %B %Y")

            # Third column may contain multiple bin types separated by line breaks
            # .stripped_strings yields a generator over all non-whitespace text segments
            bin_types = [txt for txt in cols[2].stripped_strings]

            for sub_bin in bin_types:
                data["bins"].append(
                    {
                        "type": sub_bin,
                        "collectionDate": bin_date.strftime(date_format),
                    }
                )

        return data
