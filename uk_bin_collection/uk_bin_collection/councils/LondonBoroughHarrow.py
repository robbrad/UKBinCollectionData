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

        # Construct the URI
        URI = f"https://www.harrow.gov.uk/ajax/bins?u={user_uprn}&r=12345"

        # Make the GET request
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}
        response = requests.get(URI, headers=headers, timeout=30)

        # Parse the JSON response
        bin_collection = response.json()

        # Loop through all collections and extract bin type and collection date
        for collection in bin_collection["results"]["collections"]["all"]:

            CollectTime = (collection["eventTime"]).split("T")[0]
            print(CollectTime)

            dict_data = {
                "type": collection["binType"],
                "collectionDate": datetime.strptime(CollectTime, "%Y-%m-%d").strftime(
                    "%d/%m/%Y"
                ),
            }
            bindata["bins"].append(dict_data)

        return bindata
