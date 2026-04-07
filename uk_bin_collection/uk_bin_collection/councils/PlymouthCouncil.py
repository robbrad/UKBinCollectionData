import time
from datetime import datetime

import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


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

        SESSION_URL = "https://plymouth-self.achieveservice.com/authapi/isauthenticated?uri=https%253A%252F%252Fplymouth-self.achieveservice.com%252Fen%252FAchieveForms%252F%253Fform_uri%253Dsandbox-publish%253A%252F%252FAF-Process-31283f9a-3ae7-4225-af71-bf3884e0ac1b%252FAF-Stagedba4a7d5-e916-46b6-abdb-643d38bec875%252Fdefinition.json%2526redirectlink%253D%25252Fen%2526cancelRedirectLink%253D%25252Fen%2526consentMessage%253Dyes&hostname=plymouth-self.achieveservice.com&withCredentials=true"
        API_URL = "https://plymouth-self.achieveservice.com/apibroker/runLookup"

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

        def run_lookup(lookup_id: str, data: dict) -> dict:
            params = {
                "id": lookup_id,
                "repeat_against": "",
                "noRetry": "false",
                "getOnlyTokens": "undefined",
                "log_id": "",
                "app_name": "AF-Renderer::Self",
                "_": str(int(time.time() * 1000)),
                "sid": sid,
            }
            r = s.post(API_URL, json=data, headers=headers, params=params)
            r.raise_for_status()
            response_data = r.json()
            rows_data = response_data["integration"]["transformed"]["rows_data"]
            if not isinstance(rows_data, dict):
                raise ValueError("Invalid data returned from API")
            return rows_data

        standard_data = {
            "formValues": {
                "Section 1": {
                    "number1": {"value": user_uprn},
                    "lastncoll": {"value": "0"},
                    "nextncoll": {"value": "9"},
                }
            },
        }

        standard_rows = run_lookup("5c99439d85f83", standard_data)

        collective_data = {
            "formValues": {
                "Section 1": {
                    "request_type": {"value": "GARDEN"},
                    "number1": {"value": user_uprn},
                    "UPRN": {"value": str(user_uprn)},
                }
            }
        }

        collective_rows = run_lookup("698b9c49a3c13", collective_data)

        BIN_TYPES = {
            "DO": "Brown Domestic Bin",
            "RE": "Green Recycling Bin",
            "OR": "Garden Waste Bin",
        }

        seen = set()

        for row in standard_rows.values():
            bin_type = BIN_TYPES.get(row["Round_Type"], row["Round_Type"])
            collection_date = datetime.strptime(
                row["Date"].split("T")[0], "%Y-%m-%d"
            ).strftime("%d/%m/%Y")

            key = (bin_type, collection_date)
            if key not in seen:
                seen.add(key)
                bindata["bins"].append(
                    {"type": bin_type, "collectionDate": collection_date}
                )

        for row in collective_rows.values():
            waste_type = row.get("collectiveWasteType", "").lower()
            collection_date = row.get("collectiveCollectionDate")

            if not collection_date:
                continue

            if "garden" in waste_type:
                bin_type = "Garden Waste Bin"
            elif "recycling" in waste_type or "recycl" in waste_type:
                bin_type = "Green Recycling Bin"
            elif "residual" in waste_type or "general" in waste_type:
                bin_type = "Brown Domestic Bin"
            else:
                continue

            key = (bin_type, collection_date)
            if key not in seen:
                seen.add(key)
                bindata["bins"].append(
                    {"type": bin_type, "collectionDate": collection_date}
                )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], "%d/%m/%Y")
        )

        return bindata
