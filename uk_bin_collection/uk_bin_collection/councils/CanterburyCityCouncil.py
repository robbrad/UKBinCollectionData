import time

import requests

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

        data = {"uprn": user_uprn, "usrn": "1"}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
        }

        URI = (
            "https://zbr7r13ke2.execute-api.eu-west-2.amazonaws.com/Beta/get-bin-dates"
        )

        # Make the GET request
        response = requests.post(URI, json=data, headers=headers)
        response.raise_for_status()

        # Parse the JSON response
        bin_collection = json.loads(response.json()["dates"])
        collections = {
            "General": bin_collection["blackBinDay"],
            "Recycling": bin_collection["recyclingBinDay"],
            "Food": bin_collection["foodBinDay"],
            "Garden": bin_collection["gardenBinDay"],
        }
        # Loop through each collection in bin_collection
        for collection in collections:
            print(collection)

            if len(collections[collection]) <= 0:
                continue
            for date in collections[collection]:
                date = (
                    datetime.strptime(date, "%Y-%m-%dT%H:%M:%S").strftime("%d/%m/%Y"),
                )
                dict_data = {"type": collection, "collectionDate": date[0]}
                bindata["bins"].append(dict_data)

        return bindata
