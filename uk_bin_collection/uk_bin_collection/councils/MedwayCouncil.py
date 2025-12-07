import json
from datetime import timedelta

import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        api_url = f"https://api.medway.gov.uk/api/waste/getwasteday/{user_uprn}"

        response = requests.get(api_url, verify=False)

        data = {"bins": []}

        # If the response is 200, then we can parse the data; if not, we return an empty dict
        if response.status_code == 200:
            json_data = json.loads(response.text)
            if json_data:
                next_date = datetime.strptime(
                    json_data["nextCollection"], "%Y-%m-%dT%H:%M:%S%z"
                )
                dict_data = {
                    "type": "All bins",
                    "collectionDate": next_date.strftime(date_format),
                }
                data["bins"].append(dict_data)

        return data
