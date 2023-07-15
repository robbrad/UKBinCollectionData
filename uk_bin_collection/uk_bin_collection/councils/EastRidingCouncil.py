import json
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        api_url = "https://wasterecyclingapi.eastriding.gov.uk/api/RecyclingData/CollectionsData?"
        api_key = "APIKey=ekBWR8tSiv6qwMo31REEeTZ5FAiMNB"
        api_license = "&Licensee=BinCollectionWebTeam"
        postcode = kwargs.get("postcode")

        # Url is built from multiple parameters
        requests.packages.urllib3.disable_warnings()
        response = requests.get(f"{api_url}{api_key}{api_license}&Postcode={postcode}")
        json_response = json.loads(response.content)["dataReturned"]
        data = {"bins": []}
        collection_tuple = []

        # East riding seems to return the information per postcode, so we only need the first entry for the bin dates
        collection_date = datetime.strptime(
            json_response[0].get("BlueDate"), "%Y-%m-%dT%H:%M:%S"
        ).strftime(date_format)
        collection_tuple.append(("Blue Bin", collection_date))
        collection_date = datetime.strptime(
            json_response[0].get("GreenDate"), "%Y-%m-%dT%H:%M:%S"
        ).strftime(date_format)
        collection_tuple.append(("Green Bin", collection_date))
        collection_date = datetime.strptime(
            json_response[0].get("BrownDate"), "%Y-%m-%dT%H:%M:%S"
        ).strftime(date_format)
        collection_tuple.append(("Brown Bin", collection_date))

        ordered_data = sorted(collection_tuple, key=lambda x: x[1])

        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1],
            }
            data["bins"].append(dict_data)

        return data
