from bs4 import BeautifulSoup, element

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
        data = {"bins": []}
        url_base = "https://geoapi.dorsetcouncil.gov.uk/v1/services/"
        url_types = ["recyclingday", "refuseday", "foodwasteday", "gardenwasteday"]

        uprn = kwargs.get("uprn")
        # Check the UPRN is valid
        check_uprn(uprn)

        for url_type in url_types:
            response = requests.get(f"{url_base}{url_type}/{uprn}")
            if response.status_code != 200:
                raise ConnectionError(f"Could not fetch from {url_type} endpoint")
            if response.json()["values"]:
                json_data = response.json()["values"][0]

                next_collection_date = datetime.strptime(
                    json_data.get("dateNextVisit"), "%Y-%m-%d"
                )

                dict_data = {
                    "type": f"{json_data.get('type')} bin",
                    "collectionDate": next_collection_date.strftime("%d/%m/%Y"),
                }
                data["bins"].append(dict_data)

        return data
