import json
import requests
from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


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
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "connection": "keep-alive",
            "content-type": "application/json",
            "host": "www.bathnes.gov.uk",
            "referer": "https://www.bathnes.gov.uk/webforms/waste/collectionday/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-gpc": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
        }

        requests.packages.urllib3.disable_warnings()
        response = requests.get(
            f"https://www.bathnes.gov.uk/webapi/api/BinsAPI/v2/getbartecroute/{user_uprn}/true",
            headers=headers,
        )
        if response.text == "":
            raise ValueError("Error parsing data. Please check the provided UPRN. "
            "If this error continues please open an issue on GitHub.")
        json_data = json.loads(response.text)

        data = {"bins": []}

        if len(json_data["residualNextDate"]) > 0:
            dict_data = {
                "type": "Black Rubbish Bin",
                "collectionDate": datetime.strptime(
                    json_data["residualNextDate"], "%Y-%m-%dT%H:%M:%S"
                ).strftime(date_format),
            }
            data["bins"].append(dict_data)
        if len(json_data["recyclingNextDate"]) > 0:
            dict_data = {
                "type": "Recycling Containers",
                "collectionDate": datetime.strptime(
                    json_data["recyclingNextDate"], "%Y-%m-%dT%H:%M:%S"
                ).strftime(date_format),
            }
            data["bins"].append(dict_data)
        if len(json_data["organicNextDate"]) > 0:
            dict_data = {
                "type": "Garden Waste",
                "collectionDate": datetime.strptime(
                    json_data["organicNextDate"], "%Y-%m-%dT%H:%M:%S"
                ).strftime(date_format),
            }
            data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
