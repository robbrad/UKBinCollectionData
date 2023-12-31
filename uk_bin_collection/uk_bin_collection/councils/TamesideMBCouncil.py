import json
from datetime import datetime, timedelta

import requests
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        api_url = "http://lite.tameside.gov.uk/BinCollections/CollectionService.svc/GetBinCollection"
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        params = {
            "version": "3.1.4",
            "uprn": uprn,
            "token": "",
            "notification": "1",
            "operatingsystemid": "2",
            "testmode": "true",
        }

        headers = {"content-type": "text/plain"}

        requests.packages.urllib3.disable_warnings()
        response = requests.post(api_url, json=params, headers=headers)

        json_response = json.loads(response.content)["GetBinCollectionResult"]["Data"]

        today = datetime.today()
        eight_weeks = datetime.today() + timedelta(days=8 * 7)
        data = {"bins": []}
        collection_tuple = []

        bin_friendly_names = {
            "2": "Blue Bin",
            "6": "Green Bin",
            "5": "Black Bin",
            "3": "Brown Bin",
        }

        for item in json_response:
            collection_date = datetime.strptime(
                item.get("CollectionDate"), "%d/%m/%Y %H:%M:%S"
            )
            if today.date() <= collection_date.date() <= eight_weeks.date():
                bin_type = bin_friendly_names.get(item.get("BinType"))
                collection_tuple.append(
                    (bin_type, collection_date.strftime(date_format))
                )

        ordered_data = sorted(collection_tuple, key=lambda x: x[1])

        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1],
            }
            data["bins"].append(dict_data)

        return data
