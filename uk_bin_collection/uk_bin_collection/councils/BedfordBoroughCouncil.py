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

        api_url = f"https://bbaz-as-prod-bartecapi.azurewebsites.net/api/bincollections/residential/getbyuprn/{user_uprn}/35"

        requests.packages.urllib3.disable_warnings()
        response = requests.get(api_url)

        if response.status_code != 200:
            raise ConnectionError("Could not get latest data!")

        json_data = json.loads(response.text)["BinCollections"]
        data = {"bins": []}
        collections = []

        for day in json_data:
            for bin in day:
                bin_type = bin["BinType"]
                next_date = datetime.strptime(
                    bin["JobScheduledStart"], "%Y-%m-%dT%H:%M:%S"
                )
                collections.append((bin_type, next_date))

        ordered_data = sorted(collections, key=lambda x: x[1])
        data = {"bins": []}
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
