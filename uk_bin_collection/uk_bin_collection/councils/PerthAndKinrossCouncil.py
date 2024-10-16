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

        SESSION_URL = "https://pkc-self.achieveservice.com/authapi/isauthenticated?uri=https%253A%252F%252Fpkc-self.achieveservice.com%252Fen%252FAchieveForms%252F%253Fform_uri%253Dsandbox-publish%253A%252F%252FAF-Process-de9223b1-a7c6-408f-aaa3-aee33fd7f7fa%252FAF-Stage-9fa33e2e-4c1b-4963-babf-4348ab8154bc%252Fdefinition.json%2526redirectlink%253D%25252Fen%2526cancelRedirectLink%253D%25252Fen%2526consentMessage%253Dyes&hostname=pkc-self.achieveservice.com&withCredentials=true"

        API_URL = "https://pkc-self.achieveservice.com/apibroker/runLookup"

        data = {
            "formValues": {
                "Bin collections": {"propertyUPRNQuery": {"value": user_uprn}}
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://pkc-self.achieveservice.com/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "5c9267cee5efe",
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

        schedule = {
            "Green Bin": [
                rows_data.get("nextGeneralWasteCollectionDate"),
                rows_data.get("nextGeneralWasteCollectionDate2nd"),
            ],
            "Blue Bin": [
                rows_data.get("nextBlueCollectionDate"),
                rows_data.get("nextBlueWasteCollectionDate2nd"),
            ],
            "Grey Bin": [
                rows_data.get("nextGreyWasteCollectionDate"),
                rows_data.get("nextGreyWasteCollectionDate2nd"),
            ],
            "Brown Bin": [
                rows_data.get("nextGardenandFoodWasteCollectionDate"),
                rows_data.get("nextGardenandFoodWasteCollectionDate2nd"),
            ],
            "Paper Waste": [
                rows_data.get("nextPaperWasteCollectionDate"),
                rows_data.get("nextPaperWasteCollectionDate2nd"),
            ],
        }

        # Format and output the schedule
        for bin_type, dates in schedule.items():
            if any(dates):
                for date in dates:
                    dict_data = {"type": bin_type, "collectionDate": date}
                    bindata["bins"].append(dict_data)

        return bindata
