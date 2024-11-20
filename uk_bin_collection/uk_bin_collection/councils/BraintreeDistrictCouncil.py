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

        user_postcode = kwargs.get("postcode")
        user_uprn = kwargs.get("uprn")
        check_postcode(user_postcode)
        check_uprn(user_uprn)
        bindata = {"bins": []}

        URI = "https://www.braintree.gov.uk/xfp/form/554"

        response = requests.get(URI)
        soup = BeautifulSoup(response.content, "html.parser")
        token = (soup.find("input", {"name": "__token"})).get("value")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Referer": "https://www.braintree.gov.uk/xfp/form/554",
        }

        form_data = {
            "__token": token,
            "page": "5730",
            "locale": "en_GB",
            "qe15dda0155d237d1ea161004d1839e3369ed4831_0_0": user_postcode,
            "qe15dda0155d237d1ea161004d1839e3369ed4831_1_0": user_uprn,
            "next": "Next",
        }
        collection_lookup = requests.post(URI, data=form_data, headers=headers)
        collection_lookup.raise_for_status()
        for results in BeautifulSoup(collection_lookup.text, "html.parser").find_all(
            "div", class_="date_display"
        ):
            collection_info = results.text.strip().split("\n")
            collection_type = collection_info[0].strip()

            # Skip if no collection date is found
            if len(collection_info) < 2:
                continue

            collection_date = collection_info[1].strip()

            dict_data = {
                "type": collection_type,
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
