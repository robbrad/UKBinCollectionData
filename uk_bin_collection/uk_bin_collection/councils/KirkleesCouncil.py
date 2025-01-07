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

        SESSION_URL = "https://my.kirklees.gov.uk/authapi/isauthenticated?uri=https%253A%252F%252Fmy.kirklees.gov.uk%252Fservice%252FBins_and_recycling___Manage_your_bins&hostname=my.kirklees.gov.uk&withCredentials=true"

        API_URL = "https://my.kirklees.gov.uk/apibroker/runLookup"

        data = {
            "formValues": {"Search": {"validatedUPRN": {"value": user_uprn}}},
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://my.kirklees.gov.uk/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "65e08e60b299d",
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

        for bin_id, bin_info in rows_data.items():
            label = bin_info.get("label", "Unknown")
            next_collection_date = bin_info.get("NextCollectionDate", "Unknown")
            # Convert the date string into a readable format
            try:
                formatted_date = datetime.strptime(
                    next_collection_date, "%Y-%m-%dT%H:%M:%S"
                ).strftime(date_format)
            except ValueError:
                formatted_date = "Unknown"

            dict_data = {"type": label, "collectionDate": formatted_date}
            bindata["bins"].append(dict_data)

        return bindata
