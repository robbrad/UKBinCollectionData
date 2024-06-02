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

    def parse_date(self, date_str):
        months = {
            "Jan": "01",
            "Feb": "02",
            "Mar": "03",
            "Apr": "04",
            "May": "05",
            "Jun": "06",
            "Jul": "07",
            "Aug": "08",
            "Sep": "09",
            "Oct": "10",
            "Nov": "11",
            "Dec": "12",
        }
        day, date, month_abbr, year = date_str.split()
        month = months[month_abbr]
        return f"{date}/{month}/{year}"

    def parse_data(self, page: str, **kwargs) -> dict:
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        # Initialize the bin data structure
        bin_data = {"bins": []}

        # Find the table with collection dates
        table = soup.find("table", class_="my-area")

        # Extract the rows containing the bin collection information
        rows = table.find_all("tr")

        # Loop through the rows and extract bin data
        for row in rows:
            cells = row.find_all("td")
            if len(cells) == 2:
                bin_type = cells[0].get_text(strip=True)
                collection_date = cells[1].get_text(strip=True)

                if "Next refuse" in bin_type:
                    bin_data["bins"].append(
                        {
                            "type": "refuse",
                            "collectionDate": self.parse_date(collection_date),
                        }
                    )
                elif "Next recycling" in bin_type:
                    bin_data["bins"].append(
                        {
                            "type": "recycling",
                            "collectionDate": self.parse_date(collection_date),
                        }
                    )

        return bin_data
