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

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        SESSION_URL = "https://my.dudley.gov.uk/authapi/isauthenticated?uri=https%253A%252F%252Fmy.dudley.gov.uk%252Fen%252FAchieveForms%252F%253Fform_uri%253Dsandbox-publish%253A%252F%252FAF-Process-373f5628-9aae-4e9e-ae09-ea7cd0588201%252FAF-Stage-52ec040b-10e6-440f-b964-23f924741496%252Fdefinition.json%2526redirectlink%253D%25252Fen%2526cancelRedirectLink%253D%25252Fen%2526consentMessage%253Dyes&hostname=my.dudley.gov.uk&withCredentials=true"

        API_URL = "https://my.dudley.gov.uk/apibroker/runLookup"

        data = {
            "formValues": {
                "My bins": {
                    "uprnToCheck": {"value": user_uprn},
                }
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://my.dudley.gov.uk/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "64899d4c2574c",
            "repeat_against": "",
            "noRetry": "true",
            "getOnlyTokens": "undefined",
            "log_id": "",
            "app_name": "AF-Renderer::Self",
            # unix_timestamp
            "_": str(int(time.time() * 1000)),
            "sid": sid,
        }
        r = s.post(API_URL, json=data, headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
        rows_data = data["integration"]["transformed"]["rows_data"]["0"]
        if not isinstance(rows_data, dict):
            raise ValueError("Invalid data returned from API")
        BIN_TYPES = [
            ("refuseDate", "Refuse"),
            ("recyclingDate", "Recycling"),
            ("gardenDate", "Garden Waste"),
        ]
        bin_type_dict = dict(BIN_TYPES)

        for row in rows_data.items():
            if (row[0].endswith("Date")) and not row[0].endswith("EndDate"):
                if row[1]:
                    bin_type = bin_type_dict.get(row[0], row[0])
                    collection_date = datetime.strptime(row[1], "%Y-%m-%d").strftime(
                        "%d/%m/%Y"
                    )
                    dict_data = {"type": bin_type, "collectionDate": collection_date}
                    bindata["bins"].append(dict_data)

        return bindata
