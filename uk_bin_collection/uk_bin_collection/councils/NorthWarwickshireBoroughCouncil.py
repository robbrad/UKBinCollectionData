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

        SESSION_URL = "https://nwarks-ss.achieveservice.com/authapi/isauthenticated"

        API_URL = "https://nwarks-ss.achieveservice.com/apibroker/runLookup"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://nwarks-ss.achieveservice.com/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "695fc5d469d65",
            "repeat_against": "",
            "noRetry": "true",
            "getOnlyTokens": "undefined",
            "log_id": "",
            "app_name": "AF-Renderer::Self",
            # unix_timestamp
            "_": str(int(time.time() * 1000)),
            "sid": sid,
        }
        data = {
            "formValues": {
                "Collection Details": {
                    "testOrLive": {
                        "value": "Live",
                    },
                },
            },
        }

        r = s.post(API_URL, json=data, headers=headers, params=params)
        r.raise_for_status()

        form_data = r.json()
        rows_data = form_data["integration"]["transformed"]["rows_data"]["0"]
        if not isinstance(rows_data, dict):
            raise ValueError("Invalid data returned from API")
        token = rows_data["AuthenticateResponse"]

        data = {
            "formValues": {
                "Collection Details": {
                    "AuthenticateResponse": {
                        "value": token,
                    },
                    "uprn": {
                        "value": user_uprn,
                    },
                    "dateTodayFormatted": {
                        "value": datetime.now().strftime("%Y-%m-%d"),
                    },
                    "date4WeeksFormatted": {
                        "value": (datetime.now() + timedelta(weeks=12)).strftime(
                            "%Y-%m-%d"
                        ),
                    },
                },
            },
        }

        params = {
            "id": "6964f19aac313",
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

        form_data = r.json()
        food_waste = form_data["integration"]["transformed"]["rows_data"]

        params = {
            "id": "6964f19d080c5",
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

        form_data = r.json()
        refuse = form_data["integration"]["transformed"]["rows_data"]

        params = {
            "id": "6964f19bc2e2e",
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

        form_data = r.json()
        recycling = form_data["integration"]["transformed"]["rows_data"]

        params = {
            "id": "695fc85344bb3",
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

        form_data = r.json()
        garden = form_data["integration"]["transformed"]["rows_data"]

        if food_waste:
            for key, item in food_waste.items():
                dict_data = {
                    "type": item["JobName"].strip(),
                    "collectionDate": item["Date"],
                }
                bindata["bins"].append(dict_data)
        if refuse:
            for key, item in refuse.items():
                dict_data = {
                    "type": item["JobName"].strip(),
                    "collectionDate": item["Date"],
                }
                bindata["bins"].append(dict_data)
        if recycling:
            for key, item in recycling.items():
                dict_data = {
                    "type": item["JobName"].strip(),
                    "collectionDate": item["Date"],
                }
                bindata["bins"].append(dict_data)
        if garden:
            for key, item in garden.items():
                dict_data = {
                    "type": item["JobName"].strip(),
                    "collectionDate": item["Date"],
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
