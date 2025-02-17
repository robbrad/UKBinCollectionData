from datetime import datetime, timedelta

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

        URI = f"https://www.runnymede.gov.uk/homepage/150/check-your-bin-collection-day?address={user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        soup = BeautifulSoup(response.text, "html.parser")

        div = soup.find("div", class_="widget-bin-collection")

        table = div.find("table")

        tbody = table.find("tbody")

        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            bin_type = tds[0].text.strip()
            date_text = tds[1].text.strip()

            dict_data = {
                "type": bin_type,
                "collectionDate": (
                    datetime.strptime(date_text, "%A, %d %B %Y")
                ).strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
