import requests

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

        """
        Fetches and parsees bin collection entries for a given UPRN from Harlow Council's self-serve page.
        
        Parameters:
            uprn (str): Unique Property Reference Number provided via kwargs["uprn"]; validated with `check_uprn`.
        
        Returns:
            dict: A dictionary with a "bins" key mapping to a list of collection entries. Each entry is a dict with:
                - "type": the bin type as a trimmed string.
                - "collectionDate": the collection date formatted according to `date_format`.
        """
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        }

        params = {
            "uprn": user_uprn,
        }

        response = requests.get(
            "https://selfserve.harlow.gov.uk/appshost/firmstep/self/apps/custompage/bincollectionsecho",
            params=params,
            headers=headers,
            timeout=30,
        )

        soup = BeautifulSoup(response.text, features="html.parser")

        summary = soup.find("div", {"class": "summary"})
        collectionrows = summary.find_all("div", {"class": "collectionsrow"})

        for collectionrow in collectionrows:
            bin_type = collectionrow.find("div", {"class": "col-xs-4"})
            collection_time = collectionrow.find("div", {"class": "col-sm-6"})

            if bin_type and collection_time:
                collectionDate = datetime.strptime(
                    collection_time.text.strip(), "%a - %d %b %Y"
                )

                dict_data = {
                    "type": bin_type.text.strip(),
                    "collectionDate": collectionDate.strftime(date_format),
                }
                bindata["bins"].append(dict_data)

        return bindata