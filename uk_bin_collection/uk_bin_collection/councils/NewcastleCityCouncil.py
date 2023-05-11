#!/usr/bin/env python3

# This script pulls (in one hit) the data from
# Newcastle City Council Bins Data
from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from datetime import datetime


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page, **kwargs) -> None:
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        for element in soup.find_all("strong"):
            # Domestic Waste is formatted differenty to other bins
            if "Green Bin (Domestic Waste) details:" in str(element):
                collectionInfo = element.next_sibling.find("br").next_element
            else:
                collectionInfo = (
                    element.next_sibling.next_sibling.next_sibling.next_sibling
                )

            bin_type = str(element)[str(element).find("(") + 1: str(element).find(")")]
            collectionDate = str(
                datetime.strptime(
                    str(collectionInfo).replace("Next collection : ", ""), "%d-%b-%Y"
                )
                .date()
                .strftime("%d/%m/%Y")
            )

            dict_data = {"BinType": bin_type, "NextCollectionDate": collectionDate}

            data["bins"].append(dict_data)

        return data
