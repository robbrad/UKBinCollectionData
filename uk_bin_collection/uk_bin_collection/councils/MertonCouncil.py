# This script pulls (in one hit) the data from Merton Council Bins Data
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
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        bin_data_dict = {"bins": []}

        # Search for the specific bin in the table using BS4
        rows = soup.find("table", class_=("collectiondays")).find_all(
            "tr",
            class_=(
                "food-caddy",
                "papercard-wheelie",
                "plastics-boxes",
                "rubbish-wheelie",
                "textiles",
                "batteries",
            ),
        )

        # Loops the Rows
        for row in rows:
            # Get all the cells
            cells = row.find_all("td")
            # First cell is the bin_type
            bin_type = cells[0].get_text().strip()
            # Date is on the second cell, second paragraph, wrapped in p
            collectionDate = cells[1].select("p > b")[2].get_text(strip=True)
            # Make each Bin element in the JSON
            dict_data = {
                "bin_type": bin_type,
                "collectionDate": datetime.strptime(
                    collectionDate, "%d %B %Y"
                ).strftime(date_format),
            }
            # # Add data to the main JSON Wrapper
            bin_data_dict["bins"].append(dict_data)

        return bin_data_dict
