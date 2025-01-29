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

        user_uprn = str(user_uprn).zfill(12)

        URI = "https://biffaleicester.co.uk/wp-admin/admin-ajax.php"

        payload = {
            "action": "get_details_api",
            "uprn": user_uprn,
        }

        headers = {
            "Origin": "https://biffaleicester.co.uk",
            "Referer": "https://biffaleicester.co.uk/services/waste-collection-days/",
            "User-Agent": "Mozilla/5.0",
        }

        # Make the GET request
        response = requests.post(URI, headers=headers, data=payload)

        # Parse the JSON response
        bin_collection = response.json()

        # Loop through each collection in bin_collection
        for collection in bin_collection["anyType"]:
            bin_type = collection["ServiceModeDesc"]
            date = collection["ServiceDueDate"]

            dict_data = {
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    date,
                    "%d/%m/%y",
                ).strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
