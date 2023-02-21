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

        for bins in soup.findAll(
            "div",
            {
                "id": lambda L: L
                and L.startswith("page_PageContentHolder_template_pnlArticleBody")
            },
        ):
            bin_type = bins.h2.text
            binDates = bins.find_all("p")
            binCollection = (
                binDates[1].get_text(strip=True).split(": ", 1)[-1].split(".", 1)[0]
            )
            data[bin_type] = binCollection
        return data
