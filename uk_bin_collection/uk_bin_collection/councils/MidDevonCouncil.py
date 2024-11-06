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

        SESSION_URL = "https://my.middevon.gov.uk/authapi/isauthenticated?uri=https%253A%252F%252Fmy.middevon.gov.uk%252Fen%252FAchieveForms%252F%253Fform_uri%253Dsandbox-publish%253A%252F%252FAF-Process-2289dd06-9a12-4202-ba09-857fe756f6bd%252FAF-Stage-eb382015-001c-415d-beda-84f796dbb167%252Fdefinition.json%2526redirectlink%253D%25252Fen%2526cancelRedirectLink%253D%25252Fen%2526consentMessage%253Dyes&hostname=my.middevon.gov.uk&withCredentials=true"

        API_URL = "https://my.middevon.gov.uk/apibroker/runLookup"

        payload = {
            "formValues": {
                "Your Address": {
                    "listAddress": {"value": user_uprn},
                },
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://my.middevon.gov.uk/fillform/?iframe_id=fillform-frame-1&db_id=",
        }

        ids = [
            "6423144f50ec0",
            "641c7ae9b4c96",
            "645e13a01dba1",
            "642315aacb919",
            "64231699483cf",
            "642421bab7478",
            "6424229605d13",
            "645e14020c9cc",
        ]

        rows_data = []

        for id in ids:
            s = requests.session()
            r = s.get(SESSION_URL)
            r.raise_for_status()
            session_data = r.json()
            sid = session_data["auth-session"]

            params = {
                "id": id,
                "repeat_against": "",
                "noRetry": "false",
                "getOnlyTokens": "undefined",
                "log_id": "",
                "app_name": "AF-Renderer::Self",
                # unix_timestamp
                "_": str(int(time.time() * 1000)),
                "sid": sid,
            }
            r = s.post(API_URL, json=payload, headers=headers, params=params)
            r.raise_for_status()
            data = r.json()
            rows_data = data["integration"]["transformed"]["rows_data"]
            if isinstance(rows_data, dict):
                date = datetime.strptime(rows_data["0"]["display"], "%d-%b-%y")
                bin_types = (rows_data["0"]["CollectionItems"]).split(" and ")

                for bin_type in bin_types:
                    dict_data = {
                        "type": bin_type,
                        "collectionDate": date.strftime(date_format),
                    }
                    bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
