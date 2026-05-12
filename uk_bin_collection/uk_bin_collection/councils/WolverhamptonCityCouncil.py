import time

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

        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        check_postcode(user_postcode)
        bindata = {"bins": []}

        user_postcode = user_postcode.replace(" ", "%20")

        URI = f"https://www.wolverhampton.gov.uk/find-my-nearest/{user_postcode}/{user_uprn}"

        response = requests.get(URI)

        soup = BeautifulSoup(response.content, "html.parser")

        jumbotron = soup.find("div", class_="jumbotron")
        if not jumbotron:
            raise ValueError("Could not find bin collection data on page")

        for bin_div in jumbotron.select("div.col-md-4"):
            h3 = bin_div.find("h3")
            if not h3:
                continue

            next_date_h4 = bin_div.find(
                "h4", text=lambda x: x and "Next date" in x
            )
            if not next_date_h4:
                continue

            service_name = h3.text.strip()
            next_date = next_date_h4.text.split(": ")[1]

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
