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
            "January": "01",
            "February": "02",
            "March": "03",
            "April": "04",
            "May": "05",
            "June": "06",
            "July": "07",
            "August": "08",
            "September": "09",
            "October": "10",
            "November": "11",
            "December": "12",
        }
        day, date, month_abbr, year = date_str.split()
        month = months[month_abbr]
        return f"{date}/{month}/{year}"

    def add_bin_types_to_collection(
        self, bin_data: {"bins": []}, collection_date: str, collectionType: str
    ):
        if "Grey Bin" in collectionType:
            bin_data["bins"].append(
                {
                    "type": "Grey Bin",
                    "collectionDate": self.parse_date(collection_date),
                }
            )
        if "Green Bin" in collectionType:
            bin_data["bins"].append(
                {
                    "type": "Green Bin",
                    "collectionDate": self.parse_date(collection_date),
                }
            )

        if "Blue Bin" in collectionType:
            bin_data["bins"].append(
                {
                    "type": "Blue Bin",
                    "collectionDate": self.parse_date(collection_date),
                }
            )

    def parse_data(self, page: str, **kwargs) -> dict:
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        # Initialize the bin data structure
        bin_data = {"bins": []}

        collectionDatesSection = soup.find("div", id="showCollectionDates")

        # Check if the section exists
        if not collectionDatesSection:
            return bin_data

        # Check for van collection message (no standard collection dates)
        van_collection_msg = collectionDatesSection.find("p")
        if van_collection_msg and "van collection" in van_collection_msg.get_text().lower():
            # This property has van collection, no standard dates available
            return bin_data

        # Find next date
        collection_date_elem = collectionDatesSection.find("p", class_="collection-date")
        if collection_date_elem:
            collection_date = collection_date_elem.getText()
            
            # convert to date
            collection_type_elem = collectionDatesSection.find("p", class_="collection-type")
            if collection_type_elem:
                collection_type = collection_type_elem.getText()
                self.add_bin_types_to_collection(bin_data, collection_date, collection_type)

        # Find the table with collection dates
        table = collectionDatesSection.find("table", class_="leisure-table")

        if table:
            # Extract the rows containing the bin collection information
            rows = table.find_all("tr")

            # Loop through the rows and extract bin data
            for row in rows:
                cells = row.find_all("td")
                if len(cells) == 2:
                    collection_date = cells[1].get_text(strip=True)
                    collection_type = cells[0].get_text(strip=True)

                    self.add_bin_types_to_collection(
                        bin_data, collection_date, collection_type
                    )

        return bin_data
