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

        # Form a JSON wrapper
        data = {"bins": []}

        # Search for the specific table using BS4
        rows = soup.find("table", {"class": re.compile("table")}).find_all("tr")

        # Loops the Rows
        for row in rows:
            cells = row.find_all("td", {"class": lambda L: L and L.startswith("service-name")})

            if len(cells) > 0:
                collectionDatesRawData = row.find_all(
                    "td", {"class": lambda L: L and L.startswith("next-service")}
                )[0].get_text(strip=True)
                collectionDate = collectionDatesRawData[16 : len(collectionDatesRawData)].split(
                    ","
                )
                bin_type = row.find_all(
                    "td", {"class": lambda L: L and L.startswith("service-name")}
                )[0].h4.get_text(strip=True)

                for collectDate in collectionDate:
                    # Make each Bin element in the JSON
                    dict_data = {
                        "bin_type": bin_type,
                        "collectionDate": collectDate,
                    }

                    # Add data to the main JSON Wrapper
                    data["bins"].append(dict_data)

        return data
