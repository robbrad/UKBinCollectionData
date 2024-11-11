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
        bindata = {"bins": []}

        URI = f"https://www.warrington.gov.uk/bin-collections/get-jobs/{user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        # Parse the JSON response
        bin_collection = response.json()

        # Loop through each collection in bin_collection
        for collection in bin_collection["schedule"]:
            bin_type = collection["Name"]
            collection_dates = collection["ScheduledStart"]

            print(f"Bin Type: {bin_type}")
            print(f"Collection Date: {collection_dates}")

            dict_data = {
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    collection_dates,
                    "%Y-%m-%dT%H:%M:%S",
                ).strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
