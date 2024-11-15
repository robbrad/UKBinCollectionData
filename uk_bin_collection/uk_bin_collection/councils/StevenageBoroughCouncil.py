import time

import requests
from dateutil.relativedelta import relativedelta

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
        # Make a BS4 object
        uprn = kwargs.get("uprn")
        check_uprn(uprn)
        bindata = {"bins": []}

        SESSION_URL = "https://stevenage-self.achieveservice.com/authapi/isauthenticated?uri=https%253A%252F%252Fstevenage-self.achieveservice.com%252Fservice%252Fmy_bin_collection_schedule&hostname=stevenage-self.achieveservice.com&withCredentials=true"
        TOKEN_URL = "https://stevenage-self.achieveservice.com/apibroker/runLookup?id=5e55337a540d4"
        API_URL = "https://stevenage-self.achieveservice.com/apibroker/runLookup"

        data = {
            "formValues": {
                "Section 1": {
                    "token": {"value": ""},
                    "LLPGUPRN": {
                        "value": uprn,
                    },
                    "MinimumDateLookAhead": {
                        "value": time.strftime("%Y-%m-%d"),
                    },
                    "MaximumDateLookAhead": {
                        "value": str(int(time.strftime("%Y")) + 1)
                        + time.strftime("-%m-%d"),
                    },
                },
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://stevenage-self.achieveservice.com/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]

        t = s.get(TOKEN_URL)
        t.raise_for_status()
        token_data = t.json()
        data["formValues"]["Section 1"]["token"]["value"] = token_data["integration"][
            "transformed"
        ]["rows_data"]["0"]["token"]

        params = {
            "id": "64ba8cee353e6",
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

        for key in rows_data:
            value = rows_data[key]
            bin_type = value["bintype"].strip()

            try:
                date = datetime.strptime(value["collectiondate"], "%A %d %B %Y").date()
            except ValueError:
                continue

            dict_data = {
                "type": bin_type,
                "collectionDate": date.strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        return bindata
