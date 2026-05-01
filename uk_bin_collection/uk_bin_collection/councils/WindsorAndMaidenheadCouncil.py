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
        data = {"bins": []}
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        api_url = f"https://forms.rbwm.gov.uk/bincollections?uprn={user_uprn}"

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        }
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, features="html.parser")

        # Get collections div
        next_collection_div = soup.find("div", {"class": "widget-bin-collections"})

        if not next_collection_div:
            return data

        for tbody in next_collection_div.find_all("tbody"):
            for tr in tbody.find_all("tr"):
                td = tr.find_all("td")
                if len(td) >= 2:
                    next_collection_type = td[0].get_text(strip=True)
                    date_text = td[1].get_text(strip=True)
                    # Dates have ordinal suffixes like "7th April 2026"
                    cleaned_date = remove_ordinal_indicator_from_date_string(date_text)
                    try:
                        next_collection_date = datetime.strptime(
                            cleaned_date.strip(), "%d %B %Y"
                        )
                    except ValueError:
                        continue
                    dict_data = {
                        "type": next_collection_type,
                        "collectionDate": next_collection_date.strftime(date_format),
                    }
                    data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
