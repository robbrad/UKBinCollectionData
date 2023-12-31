import json

import requests
from bs4 import BeautifulSoup
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

        api_url = f"https://online.bcpcouncil.gov.uk/bcp-apis/?api=BinDayLookup&uprn={user_uprn}"

        requests.packages.urllib3.disable_warnings()
        response = requests.get(api_url)
        json_data = json.loads(response.text)
        data = {"bins": []}
        collections = []

        for bin in json_data:
            bin_type = bin["BinType"]
            next_date = datetime.strptime(bin["Next"], "%m/%d/%Y %H:%M:%S %p")
            subseq_date = datetime.strptime(bin["Subsequent"], "%m/%d/%Y %H:%M:%S %p")
            collections.append((bin_type, next_date))
            collections.append((bin_type, subseq_date))

        ordered_data = sorted(collections, key=lambda x: x[1])
        data = {"bins": []}
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
