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

        SESSION_URL = "https://mytwbc.tunbridgewells.gov.uk/authapi/isauthenticated?uri=https%3A%2F%2Fmytwbc.tunbridgewells.gov.uk%2FAchieveForms%2F%3Fmode%3Dfill%26consentMessage%3Dyes%26form_uri%3Dsandbox-publish%3A%2F%2FAF-Process-e01af4d4-eb0f-4cfe-a5ac-c47b63f017ed%2FAF-Stage-88caf66c-378f-4082-ad1d-07b7a850af38%2Fdefinition.json%26process%3D1%26process_uri%3Dsandbox-processes%3A%2F%2FAF-Process-e01af4d4-eb0f-4cfe-a5ac-c47b63f017ed%26process_id%3DAF-Process-e01af4d4-eb0f-4cfe-a5ac-c47b63f017ed&hostname=mytwbc.tunbridgewells.gov.uk&withCredentials=true"

        API_URL = "https://mytwbc.tunbridgewells.gov.uk/apibroker/runLookup"

        data = {
            "formValues": {"Property": {"siteReference": {"value": user_uprn}}},
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://mytwbc.tunbridgewells.gov.uk/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "6314720683f30",
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

        for _, item in rows_data.items():
            bin_type = item["collectionType"]
            date = datetime.strptime(item["nextDateUnformatted"], "%d/%m/%Y").strftime(
                "%d/%m/%Y"
            )
            dict_data = {"type": bin_type, "collectionDate": date}
            bindata["bins"].append(dict_data)

        return bindata
