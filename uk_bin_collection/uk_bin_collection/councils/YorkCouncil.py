import json
from datetime import datetime

import requests
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        api_url = (
            "https://waste-api.york.gov.uk/api/Collections/GetBinCollectionDataForUprn/"
        )
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        requests.packages.urllib3.disable_warnings()
        response = requests.get(f"{api_url}{uprn}")
        json_response = json.loads(response.content)["services"]
        data = {"bins": []}
        collection_tuple = []

        for item in json_response:
            collection_date = datetime.strptime(
                item.get("nextCollection"), "%Y-%m-%dT%H:%M:%S"
            ).strftime(date_format)
            collection_tuple.append((item.get("service"), collection_date))

        ordered_data = sorted(collection_tuple, key=lambda x: x[1])

        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1],
            }
            data["bins"].append(dict_data)

        return data
