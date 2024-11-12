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

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        SESSION_URL = "https://my.gravesham.gov.uk/authapi/isauthenticated?uri=https%253A%252F%252Fmy.gravesham.gov.uk%252Fen%252FAchieveForms%252F%253Fform_uri%253Dsandbox-publish%253A%252F%252FAF-Process-22218d5c-c6d6-492f-b627-c713771126be%252FAF-Stage-905e87c1-144b-4a72-8932-5518ddd3e618%252Fdefinition.json%2526redirectlink%253D%25252Fen%2526cancelRedirectLink%253D%25252Fen%2526consentMessage%253Dyes&hostname=my.gravesham.gov.uk&withCredentials=true"

        API_URL = "https://my.gravesham.gov.uk/apibroker/runLookup"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://my.gravesham.gov.uk/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "5ee8854759297",
            "repeat_against": "",
            "noRetry": "false",
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
        tokenString = rows_data["tokenString"]

        # Get the current date and time
        current_datetime = datetime.now()
        future_datetime = current_datetime + relativedelta(months=1)

        # Format it using strftime
        current_datetime = current_datetime.strftime("%Y-%m-%dT%H:%M:%S")
        future_datetime = future_datetime.strftime("%Y-%m-%dT%H:%M:%S")

        data = {
            "formValues": {
                "Check your bin day": {
                    "tokenString": {
                        "value": tokenString,
                    },
                    "UPRNForAPI": {
                        "value": user_uprn,
                    },
                    "formatDateToday": {
                        "value": current_datetime,
                    },
                    "formatDateTo": {
                        "value": future_datetime,
                    },
                }
            },
        }

        params = {
            "id": "5c8f869376376",
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

        # Extract each service's relevant details for the bin schedule
        for item in rows_data.values():
            if item["Name"]:
                Bin_Types = item["Name"].split("Empty Bin ")
                for Bin_Type in Bin_Types:
                    if Bin_Type:
                        dict_data = {
                            "type": Bin_Type.strip(),
                            "collectionDate": datetime.strptime(
                                item["Date"], "%Y-%m-%dT%H:%M:%S"
                            ).strftime(date_format),
                        }
                        bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )
        return bindata
