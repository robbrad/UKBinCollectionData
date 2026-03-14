import json
import ssl

import requests
import urllib3
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CustomHttpAdapter(requests.adapters.HTTPAdapter):
    """Transport adapter" that allows us to use custom ssl_context."""

    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=self.ssl_context,
        )


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-GB,en;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/json; charset=utf-8",
            "Pragma": "no-cache",
            "Referer": "https://www.bathnes.gov.uk/webforms/waste/collectionday/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }

        session = requests.Session()
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.options |= 0x4
        session.mount("https://", CustomHttpAdapter(ctx))

        requests.packages.urllib3.disable_warnings()
        response = session.get(
            f"https://api.bathnes.gov.uk/webapi/api/BinsAPI/v2/BartecFeaturesandSchedules/CollectionSummary/{user_uprn}",
            headers=headers,
        )
        if response.text == "":
            raise ValueError(
                "Error parsing data. Please check the provided UPRN. "
                "If this error continues please open an issue on GitHub."
            )
        json_data = json.loads(response.text)

        data = {"bins": []}

        for collection in json_data:
            collection_date = datetime.fromisoformat(collection["nextCollectionDate"])
            for feature in collection["features"]:
                dict_data = {
                    "type": feature["featureDisplayName"],
                    "collectionDate": collection_date.strftime(date_format),
                }
                data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
