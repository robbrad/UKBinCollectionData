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

        SESSION_URL = "https://your.burnley.gov.uk/authapi/isauthenticated?uri=https%253A%252F%252Fyour.burnley.gov.uk%252Fen%252FAchieveForms%252F%253Fform_uri%253Dsandbox-publish%253A%252F%252FAF-Process-b41dcd03-9a98-41be-93ba-6c172ba9f80c%252FAF-Stage-edb97458-fc4d-4316-b6e0-85598ec7fce8%252Fdefinition.json%2526redirectlink%253D%25252Fen%2526cancelRedirectLink%253D%25252Fen%2526consentMessage%253Dyes&hostname=your.burnley.gov.uk&withCredentials=true"

        API_URL = "https://your.burnley.gov.uk/apibroker/runLookup"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://your.burnley.gov.uk/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]

        data = {
            "formValues": {
                "Section 1": {
                    "case_uprn1": {
                        "value": user_uprn,
                    }
                },
            },
        }

        params = {
            "id": "607fe757df87c",
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

        current_year = (datetime.now()).year
        current_month = (datetime.now()).month
        for key, value in rows_data.items():
            bin_type = value["display"].split(" - ")[0]
            collection_date = datetime.strptime(
                value["display"].split(" - ")[1], "%A %d %B"
            )

            if current_month == 12 and collection_date.month == 1:
                collection_date = collection_date.replace(year=current_year + 1)
            else:
                collection_date = collection_date.replace(year=current_year)

            dict_data = {
                "type": bin_type,
                "collectionDate": collection_date.strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        return bindata
