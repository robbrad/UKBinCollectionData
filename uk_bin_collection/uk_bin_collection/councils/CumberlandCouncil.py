from datetime import date

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
        bindata = {"bins": []}

        # Direct URL to the bin collection schedule using UPRN
        url = f"https://www.cumberland.gov.uk/bins-recycling-and-street-cleaning/waste-collections/bin-collection-schedule/view/{user_uprn}"

        # Fetch the page
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Find the content region
        content_region = soup.find("div", class_="lgd-region--content")
        if not content_region:
            return bindata

        lis = content_region.find_all("li")
        for li in lis:
            collection_day = li.find("span", class_="waste-collection__day--day")
            collection_type_str = li.find("span", class_="waste-collection__day--type")

            collection_date = collection_day.find("time")["datetime"]

            collection_type = collection_type_str.text

            collection_date = datetime.strptime(collection_date, "%Y-%m-%d")

            dict_data = {
                "type": collection_type.strip(),
                "collectionDate": collection_date.strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        # Sort by collection date
        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
