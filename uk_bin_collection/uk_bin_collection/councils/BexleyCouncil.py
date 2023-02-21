import json

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
        # User email from @Home app as UPRN
        user_email = kwargs.get("uprn")
        headers = {
            "X-country": "gb",
            "X-email": user_email,
            "Connection": "Keep-Alive",
        }

        # Sniffed from the app
        response = requests.get(
            "https://services.athomeapp.net/ServiceData/GetUserRoundJson",
            headers=headers,
        )

        # 200 is OK. Sometimes it times out and gives this, but I'm not parsing HTTP codes
        if response.status_code != 200:
            raise ValueError(
                "Error parsing API. Please check your email is correct and registered on the @Home app."
            )

        # Load in the json and only get the bins
        json_data = json.loads(response.text)["userrounds"]
        data = {"bins": []}
        collections = []

        # For each bin, run through the list of dates and add them to a collection
        for item in json_data:
            bin_type = item["containername"]
            for sched in item["nextcollectiondates"]:
                bin_collection = datetime.strptime(
                    sched["datestring"], "%d %m %Y %H:%M"
                )
                if bin_collection.date() >= datetime.now().date():
                    collections.append((bin_type, bin_collection))

        # Order the collection of bins and dates by date order, then add to dict
        ordered_data = sorted(collections, key=lambda x: x[1])
        data = {"bins": []}
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
