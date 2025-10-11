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
        # Make a BS4 object
        uprn = kwargs.get("uprn")
        # usrn = kwargs.get("paon")
        check_uprn(uprn)
        # check_usrn(usrn)
        bindata = {"bins": []}

        # uprn = uprn.zfill(12)

        SESSION_URL = "https://eastherts-self.achieveservice.com/authapi/isauthenticated?uri=https%253A%252F%252Feastherts-self.achieveservice.com%252FAchieveForms%252F%253Fmode%253Dfill%2526consentMessage%253Dyes%2526form_uri%253Dsandbox-publish%253A%252F%252FAF-Process-98782935-6101-4962-9a55-5923e76057b6%252FAF-Stage-dcd0ec18-dfb4-496a-a266-bd8fadaa28a7%252Fdefinition.json%2526process%253D1%2526process_uri%253Dsandbox-processes%253A%252F%252FAF-Process-98782935-6101-4962-9a55-5923e76057b6%2526process_id%253DAF-Process-98782935-6101-4962-9a55-5923e76057b6&hostname=eastherts-self.achieveservice.com&withCredentials=true"

        API_URL = "https://eastherts-self.achieveservice.com/apibroker/runLookup"

        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://eastherts-self.achieveservice.com/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            # unix_timestamp
            "_": str(int(time.time() * 1000)),
            "sid": sid,
        }

        params = {
            "id": "683d9ff0e299d",
            "repeat_against": "",
            "noRetry": "true",
            "getOnlyTokens": "undefined",
            "log_id": "",
            "app_name": "AF-Renderer::Self",
            # unix_timestamp
            "_": str(int(time.time() * 1000)),
            "sid": sid,
        }

        data = {
            "formValues": {
                "Collection Days": {
                    "inputUPRN": {
                        "value": uprn,
                    }
                },
            }
        }

        r = s.post(API_URL, json=data, headers=headers, params=params)
        r.raise_for_status()

        data = r.json()
        rows_data = data["integration"]["transformed"]["rows_data"]["0"]
        if not isinstance(rows_data, dict):
            raise ValueError("Invalid data returned from API")

        # Extract each service's relevant details for the bin schedule
        for key, value in rows_data.items():
            if key.endswith("NextDate"):
                BinType = key.replace("NextDate", "ServiceName")
                for key2, value2 in rows_data.items():
                    if key2 == BinType:
                        BinType = value2
                next_collection = datetime.strptime(
                    remove_ordinal_indicator_from_date_string(value), "%A %d %B"
                ).replace(year=datetime.now().year)
                if datetime.now().month == 12 and next_collection.month == 1:
                    next_collection = next_collection + relativedelta(years=1)

                dict_data = {
                    "type": BinType,
                    "collectionDate": next_collection.strftime(date_format),
                }
                bindata["bins"].append(dict_data)

        return bindata
