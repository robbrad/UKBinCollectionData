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

        URI = "https://refusecalendarapi.denbighshire.gov.uk/Csrf/token"

        token = requests.get(URI)

        token_data = token.json()

        URI = f"https://refusecalendarapi.denbighshire.gov.uk/Calendar/{user_uprn}"

        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "content-type": "application/json",
            "dnt": "1",
            "host": "refusecalendarapi.denbighshire.gov.uk",
            "referer": "https://refusecalendarapi.denbighshire.gov.uk/",
            "x-csrf-token": token_data["token"],
        }

        # Make the GET request
        response = requests.get(URI, headers=headers)

        # Parse the JSON response
        json_data = response.json()

        bin_types = {
            "refuseDate": "Refuse",
            "recyclingDate": "Recycling",
            "gardenDate": "Garden Waste",
            "ahpDate": "AHP (Assisted Household Pickup)",
            "tradeDate": "Trade Waste",
            "tradeRefuseDate": "Trade Refuse",
            "tradeRecyclingDate": "Trade Recycling",
        }

        bindata["bins"] = [
            {"type": label, "collectionDate": json_data[key]}
            for key, label in bin_types.items()
            if json_data.get(key)
        ]

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
