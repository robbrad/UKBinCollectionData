import logging

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

        checkValid = soup.find("p", id="selectedAddressResult")
        if checkValid is None:
            raise ValueError("Address/UPRN not found")

        collections = soup.find("div", id="wasteCollectionDates")

        for bins in collections.select('div[class*="hc-island"]'):
            bin_type = bins.h4.get_text(strip=True)

            # Last div.hc-island is the calendar link, skip it
            if bin_type == "Calendar":
                continue

            # Next collection date is in a span under the second p.hc-no-margin of the div.
            bin_collection = re.search(
                r"(.*) \(.*\)", bins.select("div > p > span")[0].get_text(strip=True)
            ).group(1)
            if bin_collection:
                logging.info(
                    f"Bin type: {bin_type} - Collection date: {bin_collection}"
                )
                dict_data = {
                    "type": bin_type,
                    "collectionDate": datetime.strptime(
                        bin_collection, "%A %d %B %Y"
                    ).strftime(date_format),
                }
                data["bins"].append(dict_data)

        return data
