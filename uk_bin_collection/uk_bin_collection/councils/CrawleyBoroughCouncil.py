import time
from xml.etree import ElementTree as ET

import requests
from dateutil.relativedelta import relativedelta

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        usrn = kwargs.get("paon")
        check_uprn(uprn)
        check_usrn(usrn)
        bindata = {"bins": []}

        SESSION_URL = "https://crawleybc-self.achieveservice.com/authapi/isauthenticated?uri=https%253A%252F%252Fcrawleybc-self.achieveservice.com%252Fen%252FAchieveForms%252F%253Fform_uri%253Dsandbox-publish%253A%252F%252FAF-Process-fb73f73e-e8f5-4441-9f83-8b5d04d889d6%252FAF-Stage-ec9ada91-d2d9-43bc-9730-597d15fc8108%252Fdefinition.json%2526redirectlink%253D%252Fen%2526cancelRedirectLink%253D%252Fen%2526noLoginPrompt%253D1%2526accept%253Dyes&hostname=crawleybc-self.achieveservice.com&withCredentials=true"

        API_URL = "https://crawleybc-self.achieveservice.com/apibroker/"

        currentdate = datetime.now().strftime("%d/%m/%Y")

        data = {
            "formValues": {
                "Address": {
                    "address": {
                        "value": {
                            "Address": {
                                "usrn": {
                                    "value": usrn,
                                },
                                "uprn": {
                                    "value": uprn,
                                },
                            }
                        },
                    },
                    "dayConverted": {
                        "value": currentdate,
                    },
                    "getCollection": {
                        "value": "true",
                    },
                    "getWorksheets": {
                        "value": "false",
                    },
                },
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://crawleybc-self.achieveservice.com/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "api": "RunLookup",
            "id": "5b4f0ec5f13f4",
            "repeat_against": "",
            "noRetry": "true",
            "getOnlyTokens": "undefined",
            "log_id": "",
            "app_name": "AF-Renderer::Self",
            "_": str(int(time.time() * 1000)),
            "sid": sid,
        }

        r = s.post(API_URL, json=data, headers=headers, params=params)
        r.raise_for_status()

        data = r.json()

        # The API may return data in two formats:
        # 1. Legacy JSON: integration.transformed.rows_data
        # 2. Current XML: integration.transformed.xml_data
        rows_data = None
        xml_data = None

        integration = data.get("integration", {})
        transformed = integration.get("transformed", {}) if integration else {}

        if transformed:
            rows_data_raw = transformed.get("rows_data")
            rows_data = rows_data_raw.get("0") if isinstance(rows_data_raw, dict) else None
            xml_data = transformed.get("xml_data")

        # Try legacy JSON rows_data format first
        if rows_data and isinstance(rows_data, dict):
            for key, value in rows_data.items():
                if key.endswith("DateNext") and value:
                    BinType = key.replace("DateNext", "Service")
                    for key2, value2 in rows_data.items():
                        if key2 == BinType:
                            BinType = value2
                    next_collection = datetime.strptime(value, "%A %d %B").replace(
                        year=datetime.now().year
                    )
                    if datetime.now().month == 12 and next_collection.month == 1:
                        next_collection = next_collection + relativedelta(years=1)
                    bindata["bins"].append({
                        "type": BinType,
                        "collectionDate": next_collection.strftime(date_format),
                    })

        # Try XML format if rows_data didn't yield results
        if not bindata["bins"] and xml_data:
            try:
                root = ET.fromstring(xml_data)
                fields = root.findall(".//Field")
                field_names = [f.get("Name") for f in fields]
                rows = root.findall(".//Row")
                for row in rows:
                    values = [c.text or "" for c in row]
                    row_dict = dict(zip(field_names, values))

                    for key, value in row_dict.items():
                        if key.endswith("DateNext") and value.strip():
                            service_key = key.replace("DateNext", "Service")
                            bin_type = row_dict.get(service_key, key.replace("DateNext", ""))
                            if not bin_type:
                                bin_type = key.replace("DateNext", "")
                            next_collection = datetime.strptime(value.strip(), "%A %d %B").replace(
                                year=datetime.now().year
                            )
                            if datetime.now().month == 12 and next_collection.month == 1:
                                next_collection = next_collection + relativedelta(years=1)
                            bindata["bins"].append({
                                "type": bin_type,
                                "collectionDate": next_collection.strftime(date_format),
                            })
            except ET.ParseError as e:
                raise ValueError(f"Failed to parse XML response: {e}")

        if not bindata["bins"]:
            raise ValueError("No valid collection dates found in API response")

        return bindata
