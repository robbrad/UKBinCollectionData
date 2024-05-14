import requests
import json
import urllib.parse
from dateutil.relativedelta import relativedelta
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

        data = {"bins": []}

        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-GB,en;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Already added when you pass json=
            # 'Content-Type': 'application/json',
            # 'Cookie': 'ASP.NET_SessionId=n2kxv5ssap4gobb11va1oxge',
            "Origin": "https://tdcws01.tandridge.gov.uk",
            "Pragma": "no-cache",
            "Referer": "https://tdcws01.tandridge.gov.uk/TDCWebAppsPublic/tfaBranded/408?utm_source=pressrelease&utm_medium=smposts&utm_campaign=check_my_bin_day",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.186 Safari/537.36",
        }

        params = {
            "UPRN": f"{user_uprn}",
        }

        json_data = requests.post(
            "https://tdcws01.tandridge.gov.uk/TDCWebAppsPublic/TDCMiddleware/RESTAPI/WhiteSpaceAPI/GetCompleteRecordByUPRN",
            headers=headers,
            json=params,
        ).json()["lstNextCollections"]

        for item in json_data:
            dict_data = {
                "type": item.get("Service").replace("Collection Service", "").strip(),
                "collectionDate": datetime.strptime(
                    item.get("Date"), "%d/%m/%Y %H:%M:%S"
                ).strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
