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

        API_URLS = {
            "address_search": "https://servicelayer3c.azure-api.net/wastecalendar/address/search/",
            "collection": "https://servicelayer3c.azure-api.net/wastecalendar/collection/search/{}/",
        }
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36",
        }

        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")

        # Establish session
        s = requests.Session()
        r = s.get(
            "https://www.scambs.gov.uk/recycling-and-bins/find-your-household-bin-collection-day/",
            headers=headers,
        )

        # Select address
        r = s.get(
            API_URLS["address_search"],
            headers=headers,
            params={"postCode": user_postcode}
        )
        addresses = r.json()
        address_ids = [
            x["id"] for x in addresses if x["houseNumber"].capitalize() == user_paon
        ]
        if len(address_ids) == 0:
            raise Exception(
                f"Could not match address {user_paon}, {user_postcode}")

        # Get the schedule
        r = s.get(
            API_URLS["collection"].format(address_ids[0]),
            headers=headers,
        )
        schedule = r.json()["collections"]

        data = {"bins": []}

        for collection in schedule:
            dt = datetime.strptime(
                collection["date"], "%Y-%m-%dT%H:%M:%SZ").strftime(date_format)
            for round in collection["roundTypes"]:
                dict_data = {
                    "binType": round.title(),
                    "collectionDate": dt
                }
                data["bins"].append(dict_data)

        return data
