import pandas as pd
import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    baseclass. They can also override some
    operations with a default implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_url = kwargs.get("url")

        headers = {
            "Origin": "https://www.nelincs.gov.uk",
            "Referer": "https://www.nelincs.gov.uk",
            "User-Agent": "Mozilla/5.0",
        }

        # Make the GET request
        response = requests.get(user_url, headers=headers)

        # Parse the HTML
        soup = BeautifulSoup(response.content, "html.parser")
        soup.prettify()

        data = {"bins": []}

        # Get list items that can be seen on page
        for element in soup.find_all(
            "li", {"class": "border-0 list-group-item p-3 bg-light rounded p-2"}
        ):
            element_text = element.text.strip().split("\n\n")
            element_text = [x.strip() for x in element_text]

            bin_type = element_text[1]
            collection_date = pd.Timestamp(element_text[0]).strftime(date_format)

            dict_data = {
                "type": bin_type,
                "collectionDate": collection_date,
            }
            data["bins"].append(dict_data)

        # Get hidden list items too
        for element in soup.find_all("li", {"class": "border-0 list-group-item p-3"}):
            element_text = element.text.strip().split("\n\n")
            element_text = [x.strip() for x in element_text]

            bin_type = element_text[1]
            collection_date = pd.Timestamp(element_text[0]).strftime(date_format)

            dict_data = {
                "type": bin_type,
                "collectionDate": collection_date,
            }
            data["bins"].append(dict_data)

        return data
