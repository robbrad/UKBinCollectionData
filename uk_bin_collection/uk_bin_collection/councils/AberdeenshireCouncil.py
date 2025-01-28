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

        URI = f"https://online.aberdeenshire.gov.uk/Apps/Waste-Collections/Routes/Route/{user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        soup = BeautifulSoup(response.content, features="html.parser")
        soup.prettify()

        for collection in soup.find("table").find("tbody").find_all("tr"):
            th = collection.find("th")
            if th:
                continue
            td = collection.find_all("td")
            collection_date = datetime.strptime(
                td[0].text,
                "%d/%m/%Y %A",
            )
            bin_type = td[1].text.split(" and ")

            for bin in bin_type:
                dict_data = {
                    "type": bin,
                    "collectionDate": collection_date.strftime(date_format),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
