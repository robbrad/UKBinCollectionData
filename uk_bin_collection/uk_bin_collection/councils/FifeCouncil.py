from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Get and check UPRN
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        API_URL = "https://www.fife.gov.uk/api/custom?action=powersuite_bin_calendar_collections&actionedby=bin_calendar&loadform=true&access=citizen&locale=en"
        AUTH_URL = "https://www.fife.gov.uk/api/citizen?preview=false&locale=en"
        AUTH_KEY = "Authorization"

        r = requests.get(AUTH_URL)
        r.raise_for_status()
        auth_token = r.headers[AUTH_KEY]

        post_data = {
            "name": "bin_calendar",
            "data": {
                "uprn": user_uprn,
            },
            "email": "",
            "caseid": "",
            "xref": "",
            "xref1": "",
            "xref2": "",
        }

        headers = {
            "referer": "https://www.fife.gov.uk/services/forms/bin-calendar",
            "accept": "application/json",
            "content-type": "application/json",
            AUTH_KEY: auth_token,
        }

        r = requests.post(API_URL, data=json.dumps(post_data), headers=headers)
        r.raise_for_status()

        result = r.json()

        for collection in result["data"]["tab_collections"]:
            dict_data = {
                "type": collection["colour"],
                "collectionDate": datetime.strptime(
                    collection["date"],
                    "%A, %B %d, %Y",
                ).strftime("%d/%m/%Y"),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )
        return bindata
