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

        SESSION_URL = "https://integration.aberdeencity.gov.uk/authapi/isauthenticated?uri=https%253A%252F%252Fintegration.aberdeencity.gov.uk%252Fservice%252Fbin_collection_calendar___view&hostname=integration.aberdeencity.gov.uk&withCredentials=true"

        API_URL = "https://integration.aberdeencity.gov.uk/apibroker/runLookup"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://integration.aberdeencity.gov.uk/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "583c08ffc47fe",
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
        token = rows_data["token"]

        data = {
            "formValues": {
                "Section 1": {
                    "nauprn": {
                        "value": user_uprn,
                    },
                    "token": {
                        "value": token,
                    },
                    "mindate": {
                        "value": datetime.now().strftime("%Y-%m-%d"),
                    },
                    "maxdate": {
                        "value": (datetime.now() + timedelta(days=30)).strftime(
                            "%Y-%m-%d"
                        ),
                    },
                },
            },
        }

        params = {
            "id": "5a3141caf4016",
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

        date_pattern = re.compile(r"^(.*?)(Date\d+)$")
        count_pattern = re.compile(r"^Count(.*)$")
        for key, value in rows_data.items():
            date_match = date_pattern.match(key)
            # Match count keys
            count_match = count_pattern.match(key)
            if count_match:
                continue

            # Match date keys
            date_match = date_pattern.match(key)
            if date_match:
                bin_type = date_match.group(1)
                dict_data = {
                    "type": bin_type,
                    "collectionDate": datetime.strptime(value, "%A %d %B %Y").strftime(
                        date_format
                    ),
                }
                bindata["bins"].append(dict_data)

        return bindata
