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

        bindata = {"bins": []}

        soup = BeautifulSoup(page.content, "html.parser")
        soup.prettify

        collection_divs = soup.select("div.feature-box.bins")
        if not collection_divs:
            raise Exception("No collections found")

        for collection_div in collection_divs:
            date_p = collection_div.select_one("p.date")
            if not date_p:
                continue

            # Thu 22 Aug, 2024
            date_ = datetime.strptime(date_p.text.strip(), "%a %d %b, %Y").strftime(
                "%d/%m/%Y"
            )
            bins = collection_div.select("li")
            if not bins:
                continue
            for bin in bins:
                if not bin.text.strip():
                    continue
                bin_type = bin.text.strip()

                dict_data = {
                    "type": bin_type,
                    "collectionDate": date_,
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
