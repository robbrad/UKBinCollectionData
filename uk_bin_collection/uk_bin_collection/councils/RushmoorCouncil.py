from bs4 import BeautifulSoup
from lxml import etree

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
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        }

        params = {
            "selectedAddress": user_uprn,
        }

        response = requests.get(
            "https://www.rushmoor.gov.uk/Umbraco/Api/BinLookUpWorkAround/Get?",
            params=params,
            headers=headers,
        )
        # Make a BS4 object
        soup = BeautifulSoup(response.text, features="lxml")
        soup.prettify()
        data = {"bins": []}
        collections = []

        # Convert the XML to JSON and load the next collection data
        result = soup.find("p").contents[0]

        json_data = json.loads(result)["NextCollection"]

        # Get general waste data
        if json_data.get("RefuseCollectionBinDate") is not None:
            bin_type = "Green general waste bin"
            if json_data.get("RefuseBinExceptionMessage") != "":
                bin_type += f" ({json_data.get('RefuseBinExceptionMessage')})".rstrip()
            bin_date = datetime.strptime(
                json_data.get("RefuseCollectionBinDate"), "%Y-%m-%dT%H:%M:%S"
            )
            collections.append((bin_type, bin_date))

        # Get recycling waste data
        if json_data.get("RecyclingCollectionDate") is not None:
            bin_type = "Blue recycling bin"
            if json_data.get("RecyclingExceptionMessage") != "":
                bin_type += f" ({json_data.get('RecyclingExceptionMessage')})".rstrip()
            bin_date = datetime.strptime(
                json_data.get("RecyclingCollectionDate"), "%Y-%m-%dT%H:%M:%S"
            )
            collections.append((bin_type, bin_date))

        # Get garden waste data
        if json_data.get("GardenWasteCollectionDate") is not None:
            bin_type = "Brown garden waste bin"
            if json_data.get("GardenWasteExceptionMessage") != "":
                bin_type += (
                    f" ({json_data.get('GardenWasteExceptionMessage')})".rstrip()
                )
            bin_date = datetime.strptime(
                json_data.get("GardenWasteCollectionDate"), "%Y-%m-%dT%H:%M:%S"
            )
            collections.append((bin_type, bin_date))

        # Get food waste data
        if json_data.get("FoodWasteCollectionDate") is not None:
            bin_type = "Black food waste bin"
            if json_data.get("FoodWasteExceptionMessage") != "":
                bin_type += f" ({json_data.get('FoodWasteExceptionMessage')})".rstrip()
            bin_date = datetime.strptime(
                json_data.get("FoodWasteCollectionDate"), "%Y-%m-%dT%H:%M:%S"
            )
            collections.append((bin_type, bin_date))

        # If there's no collections, raise an error
        if len(collections) < 1:
            raise ValueError("No collections found")

        # Order the collection by date, then return them
        ordered_data = sorted(collections, key=lambda x: x[1])
        for bin in ordered_data:
            dict_data = {
                "type": bin[0],
                "collectionDate": bin[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
