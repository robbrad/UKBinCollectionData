from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


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

        data = {"bins": []}

        for bins in soup.find_all("div", {"class": lambda L: L and L.startswith("bg-")}):
            for bin in bins.find_all("p"):
                if bin.find("strong"):
                    results = re.search(
                        "Next Collection:(.*?) on ([A-Za-z]+, \\d\\d? [A-Za-z]+ \\d{4})",
                        bin.find("strong").get_text(strip=True))
                    if results:
                        collection_date = datetime.strptime(results.groups()[1], "%A, %d %B %Y")
                        data["bins"].append({
                            "type": bins.h3.get_text(strip=True),
                            "collectionDate": collection_date.strftime(date_format)
                        })

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
