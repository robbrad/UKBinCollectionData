import time

import requests
from bs4 import BeautifulSoup

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

        SESSION_URL = "https://watfordbc-self.achieveservice.com/authapi/isauthenticated?uri=https%253A%252F%252Fwatfordbc-self.achieveservice.com%252Fen%252Fservice%252FBin_collections%253Faccept%253Dyes%2526consentMessageIds%255B%255D%253D4&hostname=watfordbc-self.achieveservice.com&withCredentials=true"

        API_URL = "https://watfordbc-self.achieveservice.com/apibroker/runLookup"

        data = {
            "formValues": {
                "Address": {
                    "echoUprn": {"value": user_uprn},
                },
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://watfordbc-self.achieveservice.com/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "5e79edf15b2ec",
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
        dispHTML = data["integration"]["transformed"]["rows_data"]["0"]["dispHTML"]
        soup = BeautifulSoup(dispHTML, features="html.parser")

        collections = soup.find_all("li")
        for collection in collections:
            bin_type = collection.find("h3").text
            collection_date = collection.find("strong").text.strip()
            dict_data = {"type": bin_type, "collectionDate": collection_date}
            bindata["bins"].append(dict_data)

        return bindata
