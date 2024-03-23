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

        bins = soup.find("div", {"class": "results-table-wrapper"}).find_all("div", {"class": "service-wrapper"})
        for bin in bins:
            bin_type = bin.find("h3", {"class": "service-name"}).get_text().replace("Collection", "bin").strip()
            bin_date = datetime.strptime(bin.find("td", {"class": "next-service"}).find("span", {"class": "table-label"}).next_sibling.get_text().strip(), "%d/%m/%Y")
            collections.append((bin_type, bin_date))

        ordered_data = sorted(collections, key=lambda x: x[1])
        for item in ordered_data:
            dict_data = {
                "type": item[0].capitalize(),
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
