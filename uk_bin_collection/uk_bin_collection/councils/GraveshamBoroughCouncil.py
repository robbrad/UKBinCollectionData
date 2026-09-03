import time

import requests
from dateutil.relativedelta import relativedelta

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

SESSION_URL = "https://my.gravesham.gov.uk/authapi/isauthenticated?uri=https%253A%252F%252Fmy.gravesham.gov.uk%252Fen%252FAchieveForms%252F%253Fform_uri%253Dsandbox-publish%253A%252F%252FAF-Process-22218d5c-c6d6-492f-b627-c713771126be%252FAF-Stage-905e87c1-144b-4a72-8932-5518ddd3e618%252Fdefinition.json%2526redirectlink%253D%25252Fen%2526cancelRedirectLink%253D%25252Fen%2526consentMessage%253Dyes&hostname=my.gravesham.gov.uk&withCredentials=true"

API_URL = "https://my.gravesham.gov.uk/apibroker/runLookup"


class CouncilClass(AbstractGetBinDataClass):
    """
    Gravesham Borough Council's AchieveForms "Check your bin day" form.

    Originally UPRN-only (the user had to look their UPRN up via a
    third-party site first). Now also accepts a postcode + house
    number/name, which drives the same postcode-search lookup the form
    itself uses (id `58c855b298b88`) to resolve the UPRN automatically -
    existing UPRN-only configs keep working unchanged.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        if not user_uprn:
            check_postcode(user_postcode)
            check_paon(user_paon)
        bindata = {"bins": []}

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://my.gravesham.gov.uk/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL, headers=headers)
        r.raise_for_status()
        sid = r.json()["auth-session"]

        def run_lookup(lookup_id, section_name, form_values):
            params = {
                "id": lookup_id,
                "repeat_against": "",
                "noRetry": "false",
                "getOnlyTokens": "undefined",
                "log_id": "",
                "app_name": "AF-Renderer::Self",
                # unix_timestamp
                "_": str(int(time.time() * 1000)),
                "sid": sid,
            }
            payload = {"formValues": {section_name: form_values}}
            resp = s.post(API_URL, json=payload, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()["integration"]["transformed"]["rows_data"]

        if not user_uprn:
            addresses = run_lookup(
                "58c855b298b88",
                "Section 1",
                {"postcode_search": {"value": user_postcode}},
            )
            if not isinstance(addresses, dict) or not addresses:
                raise ValueError(f"No addresses found for postcode {user_postcode}")
            paon_upper = user_paon.strip().upper()
            match = next(
                (
                    a
                    for a in addresses.values()
                    if a.get("house", "").upper() == paon_upper
                ),
                None,
            ) or next(
                (
                    a
                    for a in addresses.values()
                    if a.get("house", "").upper().startswith(paon_upper)
                ),
                None,
            )
            if not match:
                raise ValueError(
                    f"Could not match house number '{user_paon}' in address results"
                )
            user_uprn = match["uprn"]

        token_rows = run_lookup("5ee8854759297", "Section 1", {})
        tokenString = token_rows["0"]["tokenString"]

        # Get the current date and time
        current_datetime = datetime.now()
        future_datetime = current_datetime + relativedelta(months=1)

        # Format it using strftime
        current_datetime = current_datetime.strftime("%Y-%m-%dT%H:%M:%S")
        future_datetime = future_datetime.strftime("%Y-%m-%dT%H:%M:%S")

        rows_data = run_lookup(
            "5c8f869376376",
            "Check your bin day",
            {
                "tokenString": {"value": tokenString},
                "UPRNForAPI": {"value": user_uprn},
                "formatDateToday": {"value": current_datetime},
                "formatDateTo": {"value": future_datetime},
            },
        )
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
