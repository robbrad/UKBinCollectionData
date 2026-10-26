import json
from datetime import datetime

import requests

from uk_bin_collection.uk_bin_collection.common import check_uprn, date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    # Endpoint used by the bins widget on
    # https://www.canterbury.gov.uk/bins-and-waste/find-your-bin-collection-dates
    # (the old /Beta/get-bin-dates endpoint now returns 403 for every request).
    API_URL = "https://n6ljrw455m.execute-api.eu-west-2.amazonaws.com/prod/get-bin-dates"

    BIN_TYPES = {
        "blackBinDay": "General",
        "recyclingBinDay": "Recycling",
        "redRecyclingBinDay": "Red Recycling",
        "blueRecyclingBinDay": "Blue Recycling",
        "foodBinDay": "Food",
        "communalFoodBinDay": "Communal Food",
        "gardenBinDay": "Garden",
    }

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        # The API keys on the UPRN; the USRN is required in the payload but
        # its value is not used for the lookup.
        data = {"uprn": str(user_uprn), "usrn": "1"}

        # The API Gateway rejects requests without a browser-like User-Agent.
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
            "Origin": "https://www.canterbury.gov.uk",
            "Referer": "https://www.canterbury.gov.uk/",
        }

        response = requests.post(self.API_URL, json=data, headers=headers, timeout=30)
        response.raise_for_status()

        dates = response.json().get("dates")
        # Older versions of the API returned the dates as a JSON string
        if isinstance(dates, str):
            dates = json.loads(dates)
        if not dates:
            raise ValueError(f"No collection data returned for UPRN {user_uprn}")

        for key, bin_type in self.BIN_TYPES.items():
            for date in dates.get(key) or []:
                collection_date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
                bindata["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )

        if not bindata["bins"]:
            raise ValueError(f"No collections found for UPRN {user_uprn}")

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )
        return bindata
