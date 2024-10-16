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
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        check_postcode(user_postcode)
        bindata = {"bins": []}

        SESSION_URL = "https://contact.lincoln.gov.uk/authapi/isauthenticated?uri=https://contact.lincoln.gov.uk/AchieveForms/?mode=fill&consentMessage=yes&form_uri=sandbox-publish://AF-Process-503f9daf-4db9-4dd8-876a-6f2029f11196/AF-Stage-a1c0af0f-fec1-4419-80c0-0dd4e1d965c9/definition.json&process=1&process_uri=sandbox-processes://AF-Process-503f9daf-4db9-4dd8-876a-6f2029f11196&process_id=AF-Process-503f9daf-4db9-4dd8-876a-6f2029f11196&hostname=contact.lincoln.gov.uk&withCredentials=true"

        API_URL = "https://contact.lincoln.gov.uk/apibroker/runLookup"

        data = {
            "formValues": {
                "Section 1": {
                    "chooseaddress": {"value": user_uprn},
                    "postcode": {"value": user_postcode},
                }
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://contact.lincoln.gov.uk/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "62aafd258f72c",
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

        BIN_TYPES = [
            ("refusenextdate", "Black Bin", "refuse_freq"),
            ("recyclenextdate", "Brown Bin", "recycle_freq"),
            ("gardennextdate", "Green Bin", "garden_freq"),
        ]

        for uprn, data in rows_data.items():
            if uprn != user_uprn:
                continue
            for key, bin_type, freq in BIN_TYPES:
                if not data[key]:
                    continue
                offsets = [0]
                if data[freq] == "fortnightly":
                    offsets.extend(list(range(14, 30, 14)))
                elif data[freq] == "weekly":
                    offsets.extend(list(range(7, 30, 7)))
                date = datetime.strptime(data[key], "%Y-%m-%d").date()
                for offset in offsets:
                    dict_data = {
                        "type": bin_type,
                        "collectionDate": (date + timedelta(days=offset)).strftime(
                            "%d/%m/%Y"
                        ),
                    }
                    bindata["bins"].append(dict_data)

        return bindata
