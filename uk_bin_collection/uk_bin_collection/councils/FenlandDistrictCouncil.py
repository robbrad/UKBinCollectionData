import json

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

        headers = {
            'Accept':           'application/json, text/javascript, */*; q=0.01',
            'Accept-Language':  'en-GB,en;q=0.7',
            'Connection':       'keep-alive',
            'Content-Type':     'application/json; charset=utf-8',
            'Referer':          'https://www.fenland.gov.uk/article/13114/?uprn=200002981143&lat=52.665569590474&lng=0.177905443639&postcode=PE13+3SL&line1=20+Felsted+Avenue&rad=5m&layers=2%2C3%2C1',
            'Sec-Fetch-Dest':   'empty',
            'Sec-Fetch-Mode':   'cors',
            'Sec-Fetch-Site':   'same-origin',
            'Sec-GPC':          '1',
            'User-Agent':       'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }

        # It needs lat and lng for point data, but we don't need it >:)
        params = {
            'type':    'loadlayer',
            'layerId': '2',
            'uprn':    user_uprn,
            'lat':     '0.000000000001',
            'lng':     '0.000000000001',
        }

        response = requests.get('https://www.fenland.gov.uk/article/13114/', params=params, headers=headers)

        json_data = json.loads(response.text)["features"][0]["properties"]["upcoming"]
        data = {"bins": []}

        for item in json_data:
            collections_list = item["collections"]
            for bin in collections_list:
                bin_type = bin["desc"]
                bin_date = datetime.strptime(bin["collectionDate"], "%Y-%m-%dT%H:%M:%SZ").strftime(date_format)
                dict_data = {
                    "type":           bin_type,
                    "collectionDate": bin_date,
                }
                data["bins"].append(dict_data)

        return data
