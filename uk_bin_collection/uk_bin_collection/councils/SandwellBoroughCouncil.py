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
        # Establish a session and grab the session ID
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]

        payload = {
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
        base_params = {
            "repeat_against": "",
            "noRetry": "false",
            "getOnlyTokens": "undefined",
            "log_id": "",
            "app_name": "AF-Renderer::Self",
            # unix_timestamp
            "_": str(int(time.time() * 1000)),
            "sid": sid,
        }
        # (request_id, date field to use from response, bin type labels)
        lookups = [
            (
                "58a1a71694992",
                "DWDate",
                [
                    "Recycling (Blue)",
                    "Household Waste (Grey)",
                    "Food Waste (Brown)",
                    "Batteries",
                ],
            ),
            ("56b1cdaf6bb43", "GWDate", ["Garden Waste (Green)"]),
        ]

        for request_id, date_key, bin_types in lookups:
            params = {"id": request_id, **base_params}

            resp = s.post(API_URL, json=payload, headers=headers, params=params)
            resp.raise_for_status()
            result = resp.json()

            rows_data = result["integration"]["transformed"]["rows_data"]
            if not isinstance(rows_data, dict):
                # Garden waste for some Uprns returns an empty list
                continue

            for row in rows_data.values():
                date = row[date_key]
                for bin_type in bin_types:
                    bindata["bins"].append({"type": bin_type, "collectionDate": date})

        return bindata
