from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:

        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)
        bindata = {"bins": []}

        user_postcode = user_postcode.strip().replace(" ", "")

        URI = f"https://www.lbhf.gov.uk/bin-recycling-day/results?postcode={user_postcode}"
        UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        session = requests.session()
        session.headers.update({"User-Agent": UA})
        # Make the GET request
        response = session.get(URI)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, features="html.parser")
        results = soup.find("div", {"class": "nearest-search-results"})
        ol = results.find("ol")
        bin_collections = ol.find_all("a")

        today = datetime.now().strftime("%A")

        for bin_collection in bin_collections:
            collection_day = bin_collection.get_text().split(" - ")[0]
            collection_type = bin_collection.get_text().split(" - ")[1]

            if days_of_week.get(collection_day) == days_of_week.get(today):
                collection_day = datetime.now().strftime(date_format)
            else:
                collection_day = get_next_day_of_week(collection_day)

            dict_data = {
                "type": collection_type,
                "collectionDate": collection_day,
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
