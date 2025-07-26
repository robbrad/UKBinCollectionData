import time

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
        bindata = {"bins": []}

        URI = f"https://www.swindon.gov.uk/info/20122/rubbish_and_recycling_collection_days?addressList={user_uprn}&uprnSubmit=Yes"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}

        # Make the GET request
        response = requests.get(URI, headers=headers)

        # Parse the JSON response
        soup = BeautifulSoup(response.text, "html.parser")

        bin_collection_content = soup.find_all(
            "div", {"class": "bin-collection-content"}
        )
        for content in bin_collection_content:
            content_left = content.find("div", {"class": "content-left"})
            content_right = content.find("div", {"class": "content-right"})
            if content_left and content_right:

                bin_types = content_left.find("h3").text.split(" and ")
                for bin_type in bin_types:

                    collection_date = datetime.strptime(
                        content_right.find(
                            "span", {"class": "nextCollectionDate"}
                        ).text,
                        "%A, %d %B %Y",
                    ).strftime(date_format)

                    dict_data = {
                        "type": bin_type,
                        "collectionDate": collection_date,
                    }
                    bindata["bins"].append(dict_data)

        return bindata
