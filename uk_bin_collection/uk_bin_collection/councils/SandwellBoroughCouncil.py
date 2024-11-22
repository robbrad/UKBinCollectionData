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

        SESSION_URL = "https://my.sandwell.gov.uk/authapi/isauthenticated?uri=https%253A%252F%252Fmy.sandwell.gov.uk%252Fen%252FAchieveForms%252F%253Fform_uri%253Dsandbox-publish%253A%252F%252FAF-Process-ebaa26a2-393c-4a3c-84f5-e61564192a8a%252FAF-Stage-e4c2cb32-db55-4ff5-845c-8b27f87346c4%252Fdefinition.json%2526redirectlink%253D%25252Fen%2526cancelRedirectLink%253D%25252Fen%2526consentMessage%253Dyes&hostname=my.sandwell.gov.uk&withCredentials=true"

        API_URL = "https://my.sandwell.gov.uk/apibroker/runLookup"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://my.sandwell.gov.uk/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]

        data = {
            "formValues": {
                "Property details": {
                    "Uprn": {
                        "value": user_uprn,
                    },
                    "NextCollectionFromDate": {
                        "value": datetime.now().strftime("%Y-%m-%d"),
                    },
                },
            },
        }

        params = {
            "id": "58a1a71694992",
            "repeat_against": "",
            "noRetry": "false",
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
        rows_data = data["integration"]["transformed"]["rows_data"]
        if not isinstance(rows_data, dict):
            raise ValueError("Invalid data returned from API")
        bin_types = {
            "Recycling (Blue)",
            "Household Waste (Grey)",
            "Food Waste (Brown)",
            "Garden Waste (Green)",
        }
        for row in rows_data.items():
            date = row[1]["DWDate"]
            for bin_type in bin_types:
                dict_data = {
                    "type": bin_type,
                    "collectionDate": date,
                }
                bindata["bins"].append(dict_data)

        return bindata
