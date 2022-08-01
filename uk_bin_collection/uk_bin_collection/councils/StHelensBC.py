from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
import pandas as pd


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
        results = []
        table = soup.find("table", {"class": "multitable"})
        table_body = table.find("tbody")
        rows = table_body.find_all("tr")

        for row in rows:
            row_values = [text.text for text in row.contents]
            bin_type = row_values[0]
            for i in range(1, 4):
                # Convert date to list and remove day part
                date_as_list = row_values[i].split(" ")
                date_as_list.pop(0)

                # Add extra padding if the number is 1-9 -> 01-09
                if int(date_as_list[0]) < 10:
                    date_as_list[0] = date_as_list[0].rjust(1, "0")

                # Add the dateparts to a string
                date_as_str = " ".join(date_as_list)

                # Make into a timestamp (pandas seems to have a better tolerance)
                try:
                    collection_date = pd.Timestamp(date_as_str).strftime("%d/%m/%Y")
                except Exception as ex:
                    collection_date = "NaN"

                dict_data = {
                    "type": bin_type,
                    "collectionDate": collection_date,
                }
                data["bins"].append(dict_data)

        return data
