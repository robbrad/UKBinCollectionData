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

        data = {}

        for bins in soup.findAll("div", {"class": lambda L: L and L.startswith("bg-")}):
            bin_type = bins.h3.text
            binCollection = bins.find_all("strong")[-1].text
            data[f"{bin_type}"] = f"{binCollection}"

        return data
