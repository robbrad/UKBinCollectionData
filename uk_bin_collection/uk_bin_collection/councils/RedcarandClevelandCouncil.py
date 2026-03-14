import time

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
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)
        check_paon(user_paon)
        bindata = {"bins": []}

        URI = "https://api.eu.recollect.net/api/areas/RedcarandClevelandUK/services/50006/address-suggest"

        params = {
            "q": user_postcode,
            "locale": "en-GB",
            "_": str(int(time.time() * 1000)),
        }

        # print(params)

        # Send GET request
        response = requests.get(URI, params=params)

        addresses = response.json()

        place_id = next(
            (
                item["place_id"]
                for item in addresses
                if item.get("name", "").startswith(user_paon)
            ),
            addresses[1]["place_id"] if addresses[1] else None,
        )

        # print(addresses)
        # print(f"PlaceID - {place_id}")

        URI = (
            f"https://api.eu.recollect.net/api/places/{place_id}/services/50006/events"
        )

        after = datetime.today()
        before = after + timedelta(days=30)

        after = after.strftime("%Y-%m-%d")
        before = before.strftime("%Y-%m-%d")

        # print(after)
        # print(before)

        params = {
            "nomerge": 1,
            "hide": "reminder_only",
            "after": after,
            "before": before,
            "locale": "en-GB",
            "include_message": "email",
            "_": str(int(time.time() * 1000)),
        }

        # print(params)

        # Send GET request
        response = requests.get(URI, params=params)

        response = response.json()

        bin_collection = response["events"]

        # print(bin_collection)

        # Extract "end_day" and "name"
        events = [
            (event["end_day"], flag["name"])
            for event in bin_collection
            for flag in event.get("flags", [])
        ]

        # Print results
        for end_day, bin_type in events:

            date = datetime.strptime(end_day, "%Y-%m-%d")

            dict_data = {
                "type": bin_type,
                "collectionDate": date.strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
