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

        COLLECTION_MAP = {
            "ahtm_dates_black_bin": "Black bin",
            "ahtm_dates_brown_commingled_bin": "Brown bin",
            "ahtm_dates_blue_pulpable_bin": "Blue bin",
            "ahtm_dates_green_organic_bin": "Green Bin",
        }

        API_URL = "https://manchester.form.uk.empro.verintcloudservices.com/api/custom?action=bin_checker-get_bin_col_info&actionedby=_KDF_custom&loadform=true&access=citizen&locale=en"
        AUTH_URL = "https://manchester.form.uk.empro.verintcloudservices.com/api/citizen?archived=Y&preview=false&locale=en"
        AUTH_KEY = "Authorization"

        r = requests.get(AUTH_URL)
        r.raise_for_status()
        auth_token = r.headers[AUTH_KEY]

        post_data = {
            "name": "sr_bin_coll_day_checker",
            "data": {
                "uprn": user_uprn,
                "nextCollectionFromDate": (datetime.now() - timedelta(days=1)).strftime(
                    "%Y-%m-%d"
                ),
                "nextCollectionToDate": (datetime.now() + timedelta(days=30)).strftime(
                    "%Y-%m-%d"
                ),
            },
            "email": "",
            "caseid": "",
            "xref": "",
            "xref1": "",
            "xref2": "",
        }

        headers = {
            "referer": "https://manchester.portal.uk.empro.verintcloudservices.com/",
            "accept": "application/json",
            "content-type": "application/json",
            AUTH_KEY: auth_token,
        }

        r = requests.post(API_URL, data=json.dumps(post_data), headers=headers)
        r.raise_for_status()

        result = r.json()
        print(result["data"])

        for key, value in result["data"].items():
            if key.startswith("ahtm_dates_"):
                print(key)
                print(value)

                dates_list = [
                    datetime.strptime(date.strip(), "%d/%m/%Y %H:%M:%S").date()
                    for date in value.split(";")
                    if date.strip()
                ]

                for current_date in dates_list:
                    dict_data = {
                        "type": COLLECTION_MAP.get(key),
                        "collectionDate": current_date.strftime(date_format),
                    }
                    bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )
        return bindata
