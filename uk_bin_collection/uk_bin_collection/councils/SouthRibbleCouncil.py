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

        SESSION_URL = "https://southribble-ss.achieveservice.com/authapi/isauthenticated?uri=https%253A%252F%252Fsouthribble-ss.achieveservice.com%252FAchieveForms%252F%253Fmode%253Dfill%2526form_uri%253Dsandbox-publish%25253A%252F%252FAF-Process-d3971054-2e93-4a74-8375-494347dd13fd%252FAF-Stage-2693df73-8a5f-4e24-86b8-456ef81dd4a1%252Fdefinition.json%2526process%253D1%2526process_uri%253Dsandbox-processes%25253A%252F%252FAF-Process-d3971054-2e93-4a74-8375-494347dd13fd%2526process_id%253DAF-Process-d3971054-2e93-4a74-8375-494347dd13fd%2526accept%253Dyes%2526consentMessageIds%25255B%25255D%253D3%2526accept%253Dyes%2526consentMessageIds%255B%255D%253D3&hostname=southribble-ss.achieveservice.com&withCredentials=true"

        API_URL = "https://southribble-ss.achieveservice.com/apibroker/runLookup"

        data = {
            "formValues": {
                "Your Collections": {
                    "PickupDate": {"value": datetime.now().strftime("%Y-%m-%d")},
                },
                "Your details": {
                    "LLPGUPRN": {"value": user_uprn},
                },
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://southribble-ss.achieveservice.com/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "58ab44ef078bd",
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
        BIN_TYPES = [
            ("RCNextCollectionDate", "Household Waste (Non-Recyclable Waste)"),
            ("RENextCollectionDate", "Blue/Green Recyclable Waste"),
            ("GWNextCollectionDate", "Garden Waste Collection"),
            ("FWNextCollectionDate", "Food Waste"),
        ]
        bin_type_dict = dict(BIN_TYPES)

        for row in rows_data.items():
            if row[0].endswith("NextCollectionDate"):
                if row[1]:
                    bin_type = bin_type_dict.get(row[0], row[0])
                    collection_date = row[1]
                    dict_data = {"type": bin_type, "collectionDate": collection_date}
                    bindata["bins"].append(dict_data)

        return bindata
