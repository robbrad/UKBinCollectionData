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
        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)

        api_url = f"https://mycouncil.northampton.digital/BinRoundFinder?postcode={urllib.parse.quote(user_postcode)}"
        json_data = requests.get(api_url).json()

        data = {"bins": []}

        dict_data = {
            "type": json_data["type"].capitalize(),
            "collectionDate": datetime.strptime(
                json_data["date"], "%Y%m%d%H%M"
            ).strftime(date_format),
        }
        data["bins"].append(dict_data)

        return data
