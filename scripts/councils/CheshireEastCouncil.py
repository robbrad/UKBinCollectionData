# This script pulls (in one hit) the data from Cheshire East Council Bins Data
import re

from bs4 import BeautifulSoup
from get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str) -> dict:
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        bin_data_dict = {"bins": []}

        # Search for the specific table using BS4
        rows = soup.find("table", {"class": re.compile("job-details")}).find_all(
            "tr", {"class": re.compile("data-row")}
        )

        # Loops the Rows
        for row in rows:
            cells = row.find_all(
                "td", {"class": lambda L: L and L.startswith("visible-cell")}
            )

            labels = cells[0].find_all("label")
            bin_type = labels[2].get_text(strip=True)
            collectionDate = labels[1].get_text(strip=True)

            # Make each Bin element in the JSON
            dict_data = {
                "bin_type": bin_type,
                "collectionDate": collectionDate,
            }

            # Add data to the main JSON Wrapper
            bin_data_dict["bins"].append(dict_data)

        return bin_data_dict
