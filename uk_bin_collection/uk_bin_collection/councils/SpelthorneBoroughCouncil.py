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

        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)
        user_paon = kwargs.get("paon")
        check_paon(user_paon)
        bindata = {"bins": []}

        SESSION_URL = "https://spelthorne-self.achieveservice.com/authapi/isauthenticated?uri=https%253A%252F%252Fspelthorne-self.achieveservice.com%252Fen%252FAchieveForms%252F%253Fmode%253Dfill%2526consentMessage%253Dyes%2526form_uri%253Dsandbox-publish%253A%252F%252FAF-Process-8d0df9d6-6bd0-487e-bbfe-38815dcc780d%252FAF-Stage-bce7fc80-bcd7-45f1-bf55-a76d38dbebba%252Fdefinition.json%2526process%253D1%2526process_uri%253Dsandbox-processes%253A%252F%252FAF-Process-8d0df9d6-6bd0-487e-bbfe-38815dcc780d%2526process_id%253DAF-Process-8d0df9d6-6bd0-487e-bbfe-38815dcc780d%2526noLoginPrompt%253D1&hostname=spelthorne-self.achieveservice.com&withCredentials=true"

        API_URL = "https://spelthorne-self.achieveservice.com/apibroker/runLookup"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://spelthorne-self.achieveservice.com/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        data = {
            "formValues": {
                "Property details": {
                    "postalcode": {"value": user_postcode},
                }
            }
        }
        params = {
            "id": "59b4477d6d84e",
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

        for key, value in rows_data.items():

            address = value.get("display")

            if address.startswith(user_paon):
                user_uprn = value.get("value")
                break

        params = {
            "id": "5f97e6e09fedd",
            "repeat_against": "",
            "noRetry": "true",
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

        token = rows_data.get("tokenString")

        start_date = datetime.today() + relativedelta(weeks=2)
        last2weeks = datetime.today() - relativedelta(weeks=2)

        # Format as YYYY-MM-DD
        formatted_date = start_date.strftime("%Y-%m-%d")
        last2weeks = last2weeks.strftime("%Y-%m-%d")

        data = {
            "formValues": {
                "Property details": {
                    "uprn1": {"value": user_uprn},
                    "endDate": {"value": formatted_date},
                    "last2Weeks": {"value": last2weeks},
                    "token": {"value": token},
                }
            }
        }

        params = {
            "id": "66042a164c9a5",
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

        use_new = any(k.endswith("New") and v for k, v in rows_data.items())
        next_date_key = "NextDateNew" if use_new else "NextDateOld"

        for key, value in rows_data.items():
            if not (key.endswith("NextCollection") or key.endswith(next_date_key)):
                continue

            bin_type = key.split("NextCollection")[0]
            if bin_type == "Gw":
                bin_type = ["Garden Waste"]
            if bin_type == "Rec":
                bin_type = ["Recycling Bin", "Food Waste Bin"]
            if bin_type == "Ref":
                bin_type = ["Rubbish Bin", "Food Waste Bin"]

            try:
                date = datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                continue

            for bin in bin_type:
                dict_data = {"type": bin, "collectionDate": date}
                bindata["bins"].append(dict_data)

        return bindata
