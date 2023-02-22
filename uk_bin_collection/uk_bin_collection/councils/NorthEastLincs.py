from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

import pandas as pd


class CouncilClass(AbstractGetBinDataClass):

    """
    Concrete classes have to implement all abstract operations of the
    baseclass. They can also override some
    operations with a default implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        # Get list items that can be seen on page
        for element in soup.find_all(
            "li", {"class": "list-group-item p-0 p-3 bin-collection-item"}
        ):
            element_text = element.text.strip().split("\n\n")
            element_text = [x.strip() for x in element_text]

            bin_type = element_text[1]
            collection_date = pd.Timestamp(element_text[0]).strftime("%d/%m/%Y")

            dict_data = {
                "type": bin_type,
                "collectionDate": collection_date,
            }
            data["bins"].append(dict_data)

        # Get hidden list items too
        for element in soup.find_all(
            "li", {"class": "list-group-item p-0 p-3 bin-collection-item d-none"}
        ):
            element_text = element.text.strip().split("\n\n")
            element_text = [x.strip() for x in element_text]

            bin_type = element_text[1]
            collection_date = pd.Timestamp(element_text[0]).strftime("%d/%m/%Y")

            dict_data = {
                "type": bin_type,
                "collectionDate": collection_date,
            }
            data["bins"].append(dict_data)

        return data
