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

        URI = "https://lbhapiprod.azure-api.net"
        endpoint = f"{URI}/whitespace/GetCollectionByUprnAndDate"
        subscription_key = "2ea6a75f9ea34bb58d299a0c9f84e72e"

        # Get today's date in 'YYYY-MM-DD' format
        collection_date = datetime.now().strftime("%Y-%m-%d")

        # Define the request headers
        headers = {
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": subscription_key,
        }

        # Define the request body
        data = {
            "getCollectionByUprnAndDate": {
                "getCollectionByUprnAndDateInput": {
                    "uprn": user_uprn,
                    "nextCollectionFromDate": collection_date,
                }
            }
        }
        # Make the POST request
        response = requests.post(endpoint, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the JSON response
        response_data = response.json()

        collections = (
            response_data.get("getCollectionByUprnAndDateResponse", {})
            .get("getCollectionByUprnAndDateResult", {})
            .get("Collections", [])
        )

        for collection in collections:
            bin_type = collection["service"]
            collection_date = collection["date"]

            dict_data = {
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    collection_date,
                    "%d/%m/%Y %H:%M:%S",
                ).strftime(date_format),
            }
            bindata["bins"].append(dict_data)
        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
