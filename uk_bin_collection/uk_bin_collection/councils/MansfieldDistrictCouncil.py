import requests

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
        api_url = f'https://portal.mansfield.gov.uk/MDCWhiteSpaceWebService/WhiteSpaceWS.asmx/GetCollectionByUPRNAndDate?apiKey=mDc-wN3-B0f-f4P&UPRN={user_uprn}&coldate={datetime.now().strftime("%d/%m/%Y")}'

        response = requests.get(api_url)
        if response.status_code != 200:
            raise ConnectionError("Could not get latest data!")

        json_data = response.json()["Collections"]
        for item in json_data:

            dict_data = {
                "type": item.get("Service").split(" ")[0] + " bin",
                "collectionDate": datetime.strptime(item.get("Date"), "%d/%m/%Y %H:%M:%S").strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
