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

        URI = "https://www.sholland.gov.uk/apiserver/ajaxlibrary"

        data = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "SouthHolland.Waste.getCollectionDates",
            "params": {"UPRN": user_uprn}
        }
        # Make the GET request
        response = requests.post(URI, json=data)

        # Parse the JSON response
        bin_collection = response.json()

        # Loop through each collection in bin_collection
        for collection in bin_collection["result"]:
            bin_type = collection.get("typeDisplay")
            collection_date = collection.get("nextDate")

            dict_data = {
                "type": bin_type,
                "collectionDate": collection_date
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%Y-%m-%d")
        )

        return bindata
