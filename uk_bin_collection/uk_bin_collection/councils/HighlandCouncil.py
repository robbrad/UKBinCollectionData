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

        SESSION_URL = "https://highland-self.achieveservice.com/authapi/isauthenticated?uri=https%3A%2F%2Fhighland-self.achieveservice.com%2Fen%2Fservice%2FCheck_your_household_bin_collection_days&hostname=highland-self.achieveservice.com&withCredentials=true"

        API_URL = "https://highland-self.achieveservice.com/apibroker/runLookup"

        data = {
            "formValues": {"Your address": {"propertyuprn": {"value": user_uprn}}},
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://highland-self.achieveservice.com/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "660d44a698632",
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

        use_new = any(k.endswith("New") and v for k, v in rows_data.items())
        next_date_key = "NextDateNew" if use_new else "NextDateOld"

        for key, value in rows_data.items():
            if not (key.endswith("NextDate") or key.endswith(next_date_key)):
                continue

            bin_type = key.split("NextDate")[0]
            if bin_type == "refuse":
                bin_type = "Non-recyclable waste"
            if bin_type == "fibres":
                bin_type = "Paper, card and cardboard recycling"
            if bin_type == "containers":
                bin_type = "Plastics, metals and cartons recycling"
            if bin_type == "garden":
                bin_type = "Garden waste"
            if bin_type == "food":
                bin_type = "Food waste"

            try:
                date = datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                continue
            dict_data = {"type": bin_type, "collectionDate": date}
            bindata["bins"].append(dict_data)

        return bindata
