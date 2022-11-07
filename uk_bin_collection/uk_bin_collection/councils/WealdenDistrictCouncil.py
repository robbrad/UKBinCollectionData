from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

import requests
import json


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
            'authority':        'www.wealden.gov.uk',
            'accept':           '*/*',
            'accept-language':  'en-GB,en;q=0.7',
            'content-type':     'application/x-www-form-urlencoded; charset=UTF-8',
            # Requests sorts cookies= alphabetically
            # 'cookie': 'ARRAffinity=e45c20b343b490e3866d5d35c3dbda687e4a1357c2163c32922209862abb5872; ARRAffinitySameSite=e45c20b343b490e3866d5d35c3dbda687e4a1357c2163c32922209862abb5872',
            'origin':           'https://www.wealden.gov.uk',
            'referer':          'https://www.wealden.gov.uk/recycling-and-waste/bin-search/?uprn=10033413624',
            'sec-fetch-dest':   'empty',
            'sec-fetch-mode':   'cors',
            'sec-fetch-site':   'same-origin',
            'sec-gpc':          '1',
            'user-agent':       'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }

        data = {
            'action': 'wealden_get_collections_for_uprn',
            'uprn':   user_uprn,
        }

        response = requests.post('https://www.wealden.gov.uk/wp-admin/admin-ajax.php', headers=headers, data=data)
        json_data = json.loads(response.text)

        if json_data["status"] != "success":
            raise ValueError("Error parsing data. Please open an issue on GitHub.")

        property_data = json_data["collection"]
        data = {"bins": []}
        collections = []

        if len(property_data["refuseCollectionDate"]) > 0:
            bin_type = "Rubbish Bin"
            bin_date = datetime.strptime(property_data["refuseCollectionDate"], "%Y-%m-%dT%H:%M:%S")
            collections.append((bin_type, bin_date))
        if len(property_data["recyclingCollectionDate"]) > 0:
            bin_type = "Recycling Bin"
            bin_date = datetime.strptime(property_data["recyclingCollectionDate"], "%Y-%m-%dT%H:%M:%S")
            collections.append((bin_type, bin_date))
        if len(property_data["gardenCollectionDate"]) > 0:
            bin_type = "Garden Bin"
            bin_date = datetime.strptime(property_data["gardenCollectionDate"], "%Y-%m-%dT%H:%M:%S")
            collections.append((bin_type, bin_date))

        ordered_data = sorted(collections, key=lambda x: x[1])
        data = {"bins": []}
        for item in ordered_data:
            dict_data = {
                "type":           item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
