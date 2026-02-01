import requests
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

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

        bindata = {"bins": []}
        curr_date = datetime.today()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        soup = BeautifulSoup(page.content, features="html.parser")
        button = soup.find(
            "a",
            text="Find out which bin will be collected when and sign up for a free email reminder.",
        )

        if button and button.get("href"):
            URI = button["href"]
            # Make the GET request
            response = requests.get(URI, headers=headers)
            soup = BeautifulSoup(response.content, features="html.parser")
            divs = soup.find_all("div", {"class": "editor"})
            for div in divs:
                lis = div.find_all("li")
                for li in lis:
                    collection = li.text.split(":")
                    collection_date = datetime.strptime(
                        collection[0],
                        "%A %d %B",
                    ).replace(year=curr_date.year)
                    if curr_date.month == 12 and collection_date.month == 1:
                        collection_date = collection_date + relativedelta(years=1)
                    bin_types = collection[1].split(" and ")
                    for bin_type in bin_types:
                        dict_data = {
                            "type": bin_type,
                            "collectionDate": collection_date.strftime("%d/%m/%Y"),
                        }
                        bindata["bins"].append(dict_data)
        else:
            print("Failed to find bin schedule")

        return bindata
