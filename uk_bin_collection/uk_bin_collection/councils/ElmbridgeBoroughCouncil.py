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

        BASE_URL = "https://elmbridge-self.achieveservice.com"
        INTIAL_URL = f"{BASE_URL}/service/Your_bin_collection_days"
        AUTH_URL = f"{BASE_URL}/authapi/isauthenticated"
        AUTH_TEST = f"{BASE_URL}/apibroker/domain/elmbridge-self.achieveservice.com"
        API_URL = f"{BASE_URL}/apibroker/runLookup"

        self._session = requests.Session()
        r = self._session.get(INTIAL_URL)
        r.raise_for_status()
        params: dict[str, str | int] = {
            "uri": r.url,
            "hostname": "elmbridge-self.achieveservice.com",
            "withCredentials": "true",
        }
        r = self._session.get(AUTH_URL, params=params)
        r.raise_for_status()
        data = r.json()
        session_key = data["auth-session"]

        params = {
            "sid": session_key,
            "_": int(datetime.now().timestamp() * 1000),
        }
        r = self._session.get(AUTH_TEST, params=params)
        r.raise_for_status()

        params: dict[str, int | str] = {
            "id": "663b557cdaece",
            "repeat_against": "",
            "noRetry": "false",
            "getOnlyTokens": "undefined",
            "log_id": "",
            "app_name": "AF-Renderer::Self",
            "_": int(datetime.now().timestamp() * 1000),
            "sid": session_key,
        }
        payload = {
            "formValues": {
                "Section 1": {
                    "UPRN": {"value": user_uprn},
                }
            }
        }
        r = self._session.post(API_URL, params=params, json=payload)
        r.raise_for_status()

        data = r.json()
        collections = list(r.json()["integration"]["transformed"]["rows_data"].values())

        for collection in collections:
            date = collection["Date"]
            for service in [
                collection["Service1"],
                collection["Service2"],
                collection["Service3"],
            ]:
                if not service:
                    continue
                service = service.removesuffix(" Collection Service")

                dict_data = {
                    "type": service,
                    "collectionDate": datetime.strptime(
                        date, "%d/%m/%Y %H:%M:%S"
                    ).strftime("%d/%m/%Y"),
                }
                bindata["bins"].append(dict_data)

        return bindata
