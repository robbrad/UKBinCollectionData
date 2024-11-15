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

        URI = f"https://www.thanet.gov.uk/wp-content/mu-plugins/collection-day/incl/mu-collection-day-calls.php?pAddress={user_uprn}"

        headers = {
            "x-requested-with": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
        }

        # Make the GET request
        response = requests.get(URI, headers=headers)

        # Parse the JSON response
        bin_collection = response.json()

        # Loop through each collection in bin_collection
        for collection in bin_collection:
            bin_type = collection["type"]
            collection_date = collection["nextDate"].split(" ")[0]

            dict_data = {
                "type": bin_type,
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
