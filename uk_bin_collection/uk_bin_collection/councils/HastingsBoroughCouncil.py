from datetime import datetime, timedelta

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

        # Hastings migrated their waste web service from el.hastings.gov.uk
        # to el2.hastings.gov.uk. The old host now returns HTTP 500.
        URI = "https://el2.hastings.gov.uk/MyArea/CollectionDays.asmx/LookupCollectionDaysByService"

        payload = {"Uprn": user_uprn}

        response = requests.post(
            URI,
            json=payload,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    " (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
                ),
            },
            verify=False,
            timeout=30,
        )
        response.raise_for_status()

        # Parse the JSON response
        bin_collection = response.json()["d"]

        # Loop through each collection in bin_collection
        for collection in bin_collection:
            bin_type = collection["Service"].removesuffix("collection service").strip()
            for collection_date in collection["Dates"]:
                collection_date = datetime.fromtimestamp(
                    int(collection_date.strip("/").removeprefix("Date").strip("()"))
                    / 1000
                ) + timedelta(hours=1)

                dict_data = {
                    "type": bin_type,
                    "collectionDate": collection_date.strftime("%d/%m/%Y"),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
