import difflib
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup
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

    base_url = "https://lisburn.isl-fusion.com"

    def parse_data(self, page: str, **kwargs) -> dict:
        """
        This function will make a request to the search endpoint with the postcode, extract the
        house numbers from the responses, then retrieve the ID of the entry with the house number that matches,
        to then retrieve the bin schedule.

        The API here is a weird combination of HTML in json responses.
        """
        postcode = kwargs.get("postcode")
        paon = kwargs.get("paon")

        if not postcode:
            raise ValueError("Must provide a postcode")

        if not paon:
            raise ValueError("Must provide a house number")

        search_url = f"{self.base_url}/address/{postcode}"

        s = requests.Session()
        response = s.get(search_url)
        response.raise_for_status()

        address_data = response.json()

        address_list = address_data["html"]

        soup = BeautifulSoup(address_list, features="html.parser")

        address_by_id = {}

        for li in soup.findAll("li"):
            link = li.findAll("a")[0]
            address_id = link.attrs["href"]
            address = link.text

            address_by_id[address_id] = address

        addresses = list(address_by_id.values())

        common = difflib.SequenceMatcher(
            a=addresses[0], b=addresses[1]
        ).find_longest_match()
        extra_bit = addresses[0][common.a: common.a + common.size]

        ids_by_paon = {
            a.replace(extra_bit, ""): a_id.replace("/view/", "").replace("/", "")
            for a_id, a in address_by_id.items()
        }

        property_id = ids_by_paon.get(paon)
        if not property_id:
            raise ValueError(
                f"Invalid house number, valid values are {', '.join(ids_by_paon.keys())}"
            )

        today = date.today()
        calendar_url = (
            f"{self.base_url}/calendar/{property_id}/{today.strftime('%Y-%m-%d')}"
        )
        response = s.get(calendar_url)
        response.raise_for_status()
        calendar_data = response.json()
        next_collections = calendar_data["nextCollections"]

        collections = list(next_collections["collections"].values())

        data = {"bins": []}

        for collection in collections:
            collection_date = datetime.strptime(collection["date"], "%Y-%m-%d")
            bins = [c["name"] for c in collection["collections"].values()]

            for bin in bins:
                data["bins"].append(
                    {
                        "type": bin,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )
        return data
