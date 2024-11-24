import urllib.parse

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

        api_url = f"https://api.westnorthants.digital/openapi/v1/unified-waste-collections/{user_uprn}"
        json_data = requests.get(api_url).json()

        data = {"bins": []}

        collections = json_data["collectionItems"]
        for collection in collections:
            dict_data = {
                "type": collection["type"].capitalize(),
                "collectionDate": datetime.strptime(
                    collection["date"], "%Y-%m-%d"
                ).strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
