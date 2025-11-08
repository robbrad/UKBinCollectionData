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
        user_postcode = kwargs.get("postcode")
        user_uprn = kwargs.get("uprn")
        check_postcode(user_postcode)
        check_uprn(user_uprn)
        bindata = {"bins": []}

        SESSION_URL = "https://rochdale-self.achieveservice.com/authapi/isauthenticated?uri=https%253A%252F%252Frochdale-self.achieveservice.com%252Fservice%252FBins___view_your_waste_collection_calendar&hostname=rochdale-self.achieveservice.com&withCredentials=true"

        API_URL = "https://rochdale-self.achieveservice.com/apibroker/runLookup"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://rochdale-self.achieveservice.com/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "6846c784a46b5",
            "repeat_against": "",
            "noRetry": "true",
            "getOnlyTokens": "undefined",
            "log_id": "",
            "app_name": "AF-Renderer::Self",
            # unix_timestamp
            "_": str(int(time.time() * 1000)),
            "sid": sid,
        }

        r = s.post(API_URL, headers=headers, params=params)
        r.raise_for_status()

        data = r.json()
        rows_data = data["integration"]["transformed"]["rows_data"]["0"]
        if not isinstance(rows_data, dict):
            raise ValueError("Invalid data returned from API")
        token = rows_data["bartecToken"]

        data = {
            "formValues": {
                "Location details": {
                    "propertyUPRN": {
                        "value": user_uprn,
                    },
                    "postcode_search": {
                        "value": user_postcode,
                    },
                    "bartecToken": {
                        "value": token,
                    },
                    "dateMinimum": {
                        "value": datetime.now().strftime("%Y-%m-%d"),
                    },
                    "dateMaximum": {
                        "value": (datetime.now() + timedelta(days=30)).strftime(
                            "%Y-%m-%d"
                        ),
                    },
                },
            },
        }

        params = {
            "id": "686e9147a867e",
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
        rows_data = data["integration"]["transformed"]["rows_data"]
        if not isinstance(rows_data, dict):
            raise ValueError("Invalid data returned from API")

        for key, value in rows_data.items():
            dict_data = {
                "type": value["bartecBinType"],
                "collectionDate": datetime.strptime(
                    value["bartecBinStartDate"], "%Y-%m-%dT%H:%M:%S"
                ).strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        return bindata
