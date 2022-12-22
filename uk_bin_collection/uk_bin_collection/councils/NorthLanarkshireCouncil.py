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

        data = {"bins": []}
        for bins in soup.select('div[class^=waste-type-container]'):
            bin_type = bins.div.h3.text.strip()
            collection_date = bins.select("div > p")[0].get_text(strip=True)
            next_collection_date = bins.select("div > p")[1].get_text(strip=True)
            dict_data = {
                    "type": bin_type,
                    "collectionDate": collection_date,
                    "nextCollectionDate": next_collection_date
                }
            if collection_date:
                data["bins"].append(dict_data)

        return data
