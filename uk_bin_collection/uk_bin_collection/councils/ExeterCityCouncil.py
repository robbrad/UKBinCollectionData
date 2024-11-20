import time

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

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        URI = f"https://exeter.gov.uk/repositories/hidden-pages/address-finder/?qsource=UPRN&qtype=bins&term={user_uprn}"

        response = requests.get(URI)
        response.raise_for_status()

        data = response.json()

        soup = BeautifulSoup(data[0]["Results"], "html.parser")
        soup.prettify()

        # Extract bin schedule
        for section in soup.find_all("h2"):
            bin_type = section.text.strip()
            collection_date = section.find_next("h3").text.strip()

            dict_data = {
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    remove_ordinal_indicator_from_date_string(collection_date),
                    "%A, %d %B %Y",
                ).strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
