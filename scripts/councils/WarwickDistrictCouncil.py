# This script pulls (in one hit) the data
# from Warick District Council Bins Data

from bs4 import BeautifulSoup
from get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
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

        for element in soup.find_all("strong"):

            bin_type = element.next_element
            bin_type = bin_type.lstrip()
            collectionDateElement = element.next_sibling.next_element.next_element
            collectionDate = collectionDateElement.getText()
            dict_data = {
                "type": bin_type,
                "collectionDate": collectionDate,
            }
            data["bins"].append(dict_data)

        return data
