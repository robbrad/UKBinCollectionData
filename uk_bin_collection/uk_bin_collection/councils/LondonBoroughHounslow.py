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

        SESSION_URL = "https://my.hounslow.gov.uk/authapi/isauthenticated?uri=https%253A%252F%252Fmy.hounslow.gov.uk%252Fservice%252FWaste_and_recycling_collections&hostname=my.hounslow.gov.uk&withCredentials=true"

        API_URL = "https://my.hounslow.gov.uk/apibroker/runLookup"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://my.hounslow.gov.uk/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "655f4290810cf",
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
                "Your address": {
                    "searchUPRN": {
                        "value": user_uprn,
                    },
                    "bartecToken": {
                        "value": token,
                    },
                    "searchFromDate": {
                        "value": datetime.now().strftime("%Y-%m-%d"),
                    },
                    "searchToDate": {
                        "value": (datetime.now() + timedelta(days=30)).strftime(
                            "%Y-%m-%d"
                        ),
                    },
                },
            },
        }

        params = {
            "id": "659eb39b66d5a",
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
        rows_data = data["integration"]["transformed"]["rows_data"]["0"]
        if not isinstance(rows_data, dict):
            raise ValueError("Invalid data returned from API")

        collections = json.loads(rows_data["jobsJSON"])

        for collection in collections:
            dict_data = {
                "type": collection["jobType"],
                "collectionDate": datetime.strptime(
                    collection["jobDate"], "%Y-%m-%d"
                ).strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        return bindata
