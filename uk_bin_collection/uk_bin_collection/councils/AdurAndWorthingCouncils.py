import bs4.element
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
        collections = []

        for bin in (
            soup.find("table", {"class": "no-style bin-days"})
            .find("tbody")
            .find_all("tr")
        ):
            bin_type = bin.find("th").get_text().strip() + " bin"
            bin_dates = bin.find_all("td")[1].contents
            for date in bin_dates:
                if type(date) == bs4.element.NavigableString:
                    bin_date = datetime.strptime(date, "%A %d %b %Y")
                    collections.append((bin_type, bin_date))

        ordered_data = sorted(collections, key=lambda x: x[1])
        for item in ordered_data:
            dict_data = {
                "type": item[0].capitalize(),
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
