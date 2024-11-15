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
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        check_postcode(user_postcode)
        bindata = {"bins": []}

        user_postcode = user_postcode.replace(" ", "%20")

        URI = f"https://www.wolverhampton.gov.uk/find-my-nearest/{user_postcode}/{user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        soup = BeautifulSoup(response.content, "html.parser")

        jumbotron = soup.find("div", {"class": "jumbotron jumbotron-fluid"})

        # Find all bin entries in the row
        for bin_div in jumbotron.select("div.col-md-4"):
            service_name = bin_div.h3.text.strip()
            next_date = bin_div.find(
                "h4", text=lambda x: x and "Next date" in x
            ).text.split(": ")[1]

            dict_data = {
                "type": service_name,
                "collectionDate": datetime.strptime(
                    next_date,
                    "%B %d, %Y",
                ).strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
