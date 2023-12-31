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
        for bins in soup.select("div[class^=waste-type-container]"):
            bin_type = bins.div.h3.text.strip()
            collection_date = bins.select("div > p")[0].get_text(strip=True)
            next_collection_date = bins.select("div > p")[1].get_text(strip=True)
            if collection_date:
                # Add collection date
                dict_data = {
                    "type": bin_type,
                    "collectionDate": datetime.strptime(
                        collection_date, "%d %B %Y"
                    ).strftime(date_format),
                }
                data["bins"].append(dict_data)
                # Add next collection date
                dict_data = {
                    "type": bin_type,
                    "collectionDate": datetime.strptime(
                        next_collection_date, "%d %B %Y"
                    ).strftime(date_format),
                }
                data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
