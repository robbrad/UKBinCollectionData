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
        soup = BeautifulSoup(page, features="html.parser")
        soup.prettify()

        # Form a JSON wrapper
        data = {"bins": []}

        # Search for the specific table using BS4
        rows = soup.find(
            "tbody", {"id": lambda L: L and L.startswith("Registration:")}
        ).find_all("tr")

        # Loops the Rows
        for row in rows:

            # set the vars per bin and date for each row
            cells = row.find_all("td")
            bin_type = cells[1].get_text()
            lcDate = cells[2].get_text()
            ncDate = cells[3].get_text()
            fcDate = cells[4].get_text()

            # Make each Bin element in the JSON
            dict_data = {
                "bin_type": bin_type,
                "Last Collection Date": lcDate,
                "Next Collection Date": ncDate,
                "Following Collection Date": fcDate,
            }

            # Add data to the main JSON Wrapper
            data["bins"].append(dict_data)

        return data
