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

        URI = f"https://servicelayer3c.azure-api.net/wastecalendar/collection/search/{user_uprn}/?authority=CCC/?numberOfCollections=255"

        # Make the GET request
        response = requests.get(URI)

        # Parse the JSON response
        bin_collection = response.json()

        # Loop through each collection in bin_collection
        for collection in bin_collection["collections"]:
            bin_types = collection["roundTypes"]
            collection_date = collection["date"]

            # Loop through the dates for each collection type
            for bin_type in bin_types:
                # print(f"Bin Type: {bin_type}")
                # print(f"Collection Date: {collection_date}")

                if bin_type == "ORGANIC":
                    bin_type = "Green Bin"
                if bin_type == "RECYCLE":
                    bin_type = "Blue Bin"
                if bin_type == "DOMESTIC":
                    bin_type = "Black Bin"

                dict_data = {
                    "type": bin_type,
                    "collectionDate": datetime.strptime(
                        collection_date,
                        "%Y-%m-%dT%H:%M:%SZ",
                    ).strftime("%d/%m/%Y"),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
