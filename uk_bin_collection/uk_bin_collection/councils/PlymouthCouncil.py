import time
from datetime import datetime, timedelta

import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


SESSION_URL = "https://plymouth-self.achieveservice.com/authapi/isauthenticated?uri=https%253A%252F%252Fplymouth-self.achieveservice.com%252Fen%252FAchieveForms%252F%253Fform_uri%253Dsandbox-publish%253A%252F%252FAF-Process-31283f9a-3ae7-4225-af71-bf3884e0ac1b%252FAF-Stagedba4a7d5-e916-46b6-abdb-643d38bec875%252Fdefinition.json%2526redirectlink%253D%25252Fen%2526cancelRedirectLink%253D%25252Fen%2526consentMessage%253Dyes&hostname=plymouth-self.achieveservice.com&withCredentials=true"
API_URL = "https://plymouth-self.achieveservice.com/apibroker/runLookup"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://plymouth-self.achieveservice.com/fillform/?iframe_id=fillform-frame-1&db_id=",
}

STANDARD_LOOKUP_ID = "5c99439d85f83"
COLLECTIVE_KEY_LOOKUP_ID = "6936e38f6d376"
COLLECTIVE_JOBS_LOOKUP_ID = "698b9c49a3c13"
LOOKAHEAD_DAYS = 24


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        sid = r.json()["auth-session"]

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
            r = s.post(API_URL, json=data, headers=HEADERS, params=params)
            r.raise_for_status()
            response_data = r.json()

            transformed = response_data.get("integration", {}).get("transformed")
            if transformed is None:
                raise ValueError(
                    f"Plymouth lookup {lookup_id} returned no transformed data: {response_data}"
                )

            rows_data = transformed.get("rows_data")
            if not isinstance(rows_data, dict):
                raise ValueError(
                    f"Plymouth lookup {lookup_id} returned invalid rows_data: {response_data}"
                )

            return rows_data

        start_date = datetime.now().strftime("%Y-%m-%dT00:00:00")
        end_date = (datetime.now() + timedelta(days=LOOKAHEAD_DAYS)).strftime(
            "%Y-%m-%dT00:00:00"
        )

        standard_data = {
            "formValues": {
                "Section 1": {
                    "number1": {"value": user_uprn},
                    "lastncoll": {"value": "0"},
                    "nextncoll": {"value": "20"},
                }
            },
        }
        standard_rows = run_lookup(STANDARD_LOOKUP_ID, standard_data)

        collective_key_data = {
            "stopOnFailure": True,
            "usePHPIntegrations": True,
            "stage_id": "AF-Stagedba4a7d5-e916-46b6-abdb-643d38bec875",
            "stage_name": "Check Bin Day",
            "formId": "AF-Form-b8823128-0c85-47e1-b344-4fc81480edd0",
            "formValues": {
                "Section 1": {
                    "request_type": {"value": "GARDEN"},
                    "addressDetails": {"value": ""},
                    "number1": {"value": ""},
                    "UPRN": {"value": ""},
                    "collectiveKey": {"value": ""},
                    "collectiveUPRN": {"value": ""},
                    "collectiveGetJobStartDate": {"value": start_date},
                    "collectiveGetJobEndDate": {"value": end_date},
                    "lastncoll": {"value": "0"},
                    "nextncoll": {"value": "9"},
                    "displayChecker": {"value": "false"},
                    "hiddenPN": {"value": "Waste - Check your bin day"},
                    "productArea1": {"value": "Self"},
                    "ffDirectorate": {"value": "Place"},
                    "ffDepartment": {"value": "Street Services"},
                    "ffIntExt": {"value": "External"},
                    "ffPreSubmission": {"value": "preSubmission"},
                }
            },
            "isPublished": True,
            "formName": "Waste - Check your bin day",
            "processId": "AF-Process-31283f9a-3ae7-4225-af71-bf3884e0ac1b",
        }

        collective_rows = {}
        try:
            key_rows = run_lookup(COLLECTIVE_KEY_LOOKUP_ID, collective_key_data)
            collective_key = key_rows.get("0", {}).get("collectiveKey")

            if collective_key:
                collective_data = {
                    "stopOnFailure": True,
                    "usePHPIntegrations": True,
                    "stage_id": "AF-Stagedba4a7d5-e916-46b6-abdb-643d38bec875",
                    "stage_name": "Check Bin Day",
                    "formId": "AF-Form-b8823128-0c85-47e1-b344-4fc81480edd0",
                    "formValues": {
                        "Section 1": {
                            "request_type": {"value": "GARDEN"},
                            "addressDetails": {
                                "value": {
                                    "Section 1": {
                                        "ChooseAddress": {"value": str(user_uprn)}
                                    }
                                }
                            },
                            "number1": {"value": str(user_uprn)},
                            "UPRN": {"value": str(user_uprn)},
                            "collectiveKey": {"value": collective_key},
                            "collectiveUPRN": {"value": str(user_uprn)},
                            "collectiveGetJobStartDate": {"value": start_date},
                            "collectiveGetJobEndDate": {"value": end_date},
                        }
                    },
                    "isPublished": True,
                    "formName": "Waste - Check your bin day",
                    "processId": "AF-Process-31283f9a-3ae7-4225-af71-bf3884e0ac1b",
                }

                collective_rows = run_lookup(COLLECTIVE_JOBS_LOOKUP_ID, collective_data)
        except Exception:
            collective_rows = {}

        bin_type_dict = {
            "DO": "Brown Domestic Bin",
            "RE": "Green Recycling Bin",
            "OR": "Garden Waste Bin",
        }

        seen = set()

        for row in standard_rows.values():
            bin_type = bin_type_dict.get(row["Round_Type"], row["Round_Type"])
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
            collection_date = row.get("collectiveCollectionDate", "").strip()

            if not collection_date or waste_type == "no jobs found":
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
