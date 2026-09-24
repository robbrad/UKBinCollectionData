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
        if response.status_code == 403:
            # The council's site itself now calls this API server-side
            # (as part of a page redirect) rather than directly from the
            # browser, and even their own live site currently gets stuck
            # on a permanent loading spinner - the API returns a bare 403
            # regardless of the uprn/usrn payload sent. This looks like an
            # outage or an access restriction on the council's end, not
            # something fixable by changing what we send.
            raise ConnectionError(
                "Canterbury's bin collection API is returning 403 Forbidden "
                "- this looks like an outage or access restriction on the "
                "council's end, not this scraper. Try again later."
            )
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
