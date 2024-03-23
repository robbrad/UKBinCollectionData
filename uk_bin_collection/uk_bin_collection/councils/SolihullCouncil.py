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

        for bin in soup.find_all("div", class_="mb-4 card"):
            bin_type = bin.find("div", class_="card-title").find("h4").get_text().strip().replace("Wheelie ", "")
            bin_date_text = bin.find_all("div", class_="mt-1")[1].find("strong").get_text().strip().replace(",", "")
            bin_date = datetime.strptime(bin_date_text, "%A %d %B %Y")
            collections.append((bin_type, bin_date))

        ordered_data = sorted(collections, key=lambda x: x[1])
        for item in ordered_data:
            dict_data = {
                "type": item[0].capitalize(),
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
