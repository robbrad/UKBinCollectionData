# This script pulls (in one hit) the data from Merton Council Bins Data
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

        # Search for the specific bin in the table using BS4
        rows = soup.find("table", class_=("collectiondays")).find_all(
            "tr",
            class_=(
                "food-caddy",
                "papercard-wheelie",
                "plastics-boxes",
                "rubbish-wheelie",
                "textiles",
                "batteries",
                "garden",
            ),
        )

        possible_formats = [
            "%d %B %Y",
            "%A %d %B %Y",
        ]

        # Loops the Rows
        for row in rows:
            # Get all the cells
            cells = row.find_all("td")
            # First cell is the bin_type
            bin_type = cells[0].get_text().strip()

            # Garden waste is optional, so skip if none scheduled - causes an error if it gets into the date parsing below.
            if bin_type == "Garden waste":
                if (
                    "There are no garden waste collections scheduled for this address."
                    in cells[1].select("p")[0].get_text().strip()
                ):
                    continue

            # Date is on the second cell, second paragraph, wrapped in p
            collectionDate = None
            for format in possible_formats:
                try:
                    collectionDate = datetime.strptime(
                        cells[1].select("p > b")[2].get_text(strip=True), format
                    )
                    break  # Exit the loop if parsing is successful
                except ValueError:
                    continue

            # Add each collection to the list as a tuple
            collections.append((bin_type, collectionDate))

        ordered_data = sorted(collections, key=lambda x: x[1])
        for item in ordered_data:
            dict_data = {
                "type": item[0].capitalize(),
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
