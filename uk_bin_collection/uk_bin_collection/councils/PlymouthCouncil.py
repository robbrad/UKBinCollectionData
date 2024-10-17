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

        # SESSION_URL = "https://contact.lincoln.gov.uk/authapi/isauthenticated?uri=https://contact.lincoln.gov.uk/AchieveForms/?mode=fill&consentMessage=yes&form_uri=sandbox-publish://AF-Process-503f9daf-4db9-4dd8-876a-6f2029f11196/AF-Stage-a1c0af0f-fec1-4419-80c0-0dd4e1d965c9/definition.json&process=1&process_uri=sandbox-processes://AF-Process-503f9daf-4db9-4dd8-876a-6f2029f11196&process_id=AF-Process-503f9daf-4db9-4dd8-876a-6f2029f11196&hostname=contact.lincoln.gov.uk&withCredentials=true"
        SESSION_URL = "https://plymouth-self.achieveservice.com/authapi/isauthenticated?uri=https%253A%252F%252Fplymouth-self.achieveservice.com%252Fen%252FAchieveForms%252F%253Fform_uri%253Dsandbox-publish%253A%252F%252FAF-Process-31283f9a-3ae7-4225-af71-bf3884e0ac1b%252FAF-Stagedba4a7d5-e916-46b6-abdb-643d38bec875%252Fdefinition.json%2526redirectlink%253D%25252Fen%2526cancelRedirectLink%253D%25252Fen%2526consentMessage%253Dyes&hostname=plymouth-self.achieveservice.com&withCredentials=true"

        API_URL = "https://plymouth-self.achieveservice.com/apibroker/runLookup"

        data = {
            "formValues": {
                "Section 1": {
                    "number1": {"value": user_uprn},
                    "lastncoll": {"value": "0"},
                    "nextncoll": {"value": "9"},
                }
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://plymouth-self.achieveservice.com/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "5c99439d85f83",
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
            ("OR", "Garden Waste Bin"),
            ("DO", "Brown Domestic Bin"),
            ("RE", "Green Recycling Bin"),
        ]
        bin_type_dict = dict(BIN_TYPES)

        for row in rows_data.items():
            bin_type = bin_type_dict.get(row[1]["Round_Type"], "Unknown")
            collection_date = datetime.strptime(
                row[1]["Date"].split("T")[0], "%Y-%m-%d"
            ).strftime("%d/%m/%Y")
            dict_data = {"type": bin_type, "collectionDate": collection_date}
            bindata["bins"].append(dict_data)

        return bindata
