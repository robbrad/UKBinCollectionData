from datetime import datetime

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

        WASTE_TYPES_DATE_KEY = {
            "REFUSE": "refuseNextDate",
            "RECYCLING": "recyclingNextDate",
            "GREEN": "greenNextDate",
            "COMMUNAL REFUSE": "communalRefNextDate",
            "COMMUNAL RECYCLING": "communalRycNextDate",
        }

        URI = f"https://info.ambervalley.gov.uk/WebServices/AVBCFeeds/WasteCollectionJSON.asmx/GetCollectionDetailsByUPRN?uprn={user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        # Parse the JSON response
        bin_collection = response.json()

        # print(bin_collection)

        for bin, datge_key in WASTE_TYPES_DATE_KEY.items():
            date_ = datetime.strptime(
                bin_collection[datge_key], "%Y-%m-%dT%H:%M:%S"
            ).strftime(date_format)
            if date_ == "01/01/1":
                continue
            elif date_ == "01/01/0001":
                continue
            elif date_ == "01/01/1900":
                continue

            dict_data = {
                "type": bin,
                "collectionDate": date_,
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
