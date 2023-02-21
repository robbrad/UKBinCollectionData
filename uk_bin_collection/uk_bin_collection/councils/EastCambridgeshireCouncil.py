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

        for bins in soup.findAll("div", {"class": "row collectionsrow"}):

            # Find the collection dates
            _, bin_type, date = bins.find_all("div")
            bin_type = bin_type.text
            date = datetime.strptime(date.text, "%a - %d %b %Y").date()

            data["bins"].append({"BinType": bin_type, "collectionDate": date.isoformat()})
        return data
