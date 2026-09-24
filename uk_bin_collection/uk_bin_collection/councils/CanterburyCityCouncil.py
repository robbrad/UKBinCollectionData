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
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": "https://www.canterbury.gov.uk",
            "Referer": "https://www.canterbury.gov.uk/",
        }

        # The council retired the "Beta" stage of this API; it now 403s
        # unconditionally regardless of the uprn/usrn payload sent. "prod"
        # is the stage their own site's current front end calls.
        URI = (
            "https://n6ljrw455m.execute-api.eu-west-2.amazonaws.com/prod/get-bin-dates"
        )

        # Make the GET request
        response = requests.post(URI, json=data, headers=headers)
        if response.status_code == 403:
            # Kept as a clear signal in case a future API change reproduces
            # the same failure mode this scraper hit against the old "Beta"
            # stage, rather than surfacing a bare HTTPError.
            raise ConnectionError(
                "Canterbury's bin collection API is returning 403 Forbidden "
                "- this looks like an outage or access restriction on the "
                "council's end, not this scraper. Try again later."
            )
        response.raise_for_status()

        # Parse the JSON response
        bin_collection = response.json()["dates"]
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
