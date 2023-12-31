from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


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

        # Form a JSON wrapper
        data = {"bins": []}

        # Find section with bins in
        sections = (
            soup.find("div", {"class": "container results-table-wrapper"})
            .find("tbody")
            .find_all("tr")
        )

        # For each bin section, get the text and the list elements
        for item in sections:
            words = item.find_next("a").text.split()[1:2]
            bin_type = " ".join(words).capitalize()
            date = (
                item.find("td", {"class": "next-service"})
                .find_next("span")
                .next_sibling.strip()
            )
            next_collection = datetime.strptime(date, "%d/%m/%Y")
            dict_data = {
                "type": bin_type,
                "collectionDate": next_collection.strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
