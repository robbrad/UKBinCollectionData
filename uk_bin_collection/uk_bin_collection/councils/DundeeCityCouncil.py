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

        URI = f"https://www.dundee-mybins.co.uk/get_calendar.php?rn={user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        # Parse the JSON response
        bin_collection = response.json()

        for item in bin_collection:
            dict_data = {
                "type": item["title"],
                "collectionDate": datetime.strptime(item["start"], "%Y-%m-%d").strftime(
                    date_format
                ),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
