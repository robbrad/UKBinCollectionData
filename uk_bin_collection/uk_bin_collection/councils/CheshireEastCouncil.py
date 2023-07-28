from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Create a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")

        bin_data_dict = {"bins": []}

        # Search for the specific table using BS4
        rows = soup.find("table", {"class": "job-details"}).find_all(
            "tr", {"class": "data-row"}
        )

        # Loop through the rows
        for row in rows:
            cells = row.find_all("td", {"class": lambda L: L and L.startswith("visible-cell")})

            bin_type = cells[0].find_all("label")[2].get_text(strip=True)
            collection_date = cells[0].find_all("label")[1].get_text(strip=True)

            # Create a dictionary for each Bin element in the JSON
            dict_data = {
                "type": bin_type,
                "collectionDate": collection_date,
            }

            # Add data to the main JSON Wrapper
            bin_data_dict["bins"].append(dict_data)

        return bin_data_dict
