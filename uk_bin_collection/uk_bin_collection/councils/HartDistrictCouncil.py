import json
from datetime import datetime

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

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        URI = f"https://www.hart.gov.uk/bbd-whitespace/next-collection-dates?uri=entity%3Anode%2F172&uprn={user_uprn}"

        response = requests.get(URI)
        response_table = response.json()

        soup = BeautifulSoup(response_table[0]["data"], "html.parser")
        # Make a BS4 object
        # Find all the rows in the table
        rows = soup.find_all("tr")

        # Initialize an empty list to hold the bin data
        bins = []

        # Iterate through each row
        for row in rows:
            cells = row.find_all("td")

            # Check if there are exactly 3 cells in the row
            if len(cells) == 3:
                bin_type = cells[0].get_text(strip=True)
                collection_date = self.format_date(cells[2].get_text(strip=True))

            # Create a dictionary for each bin and append to the bins list
            bins.append({"type": bin_type, "collectionDate": collection_date})

        return {"bins": bins}

    def format_date(self, date_str):
        # Get the current date and year
        current_date = datetime.now()
        current_year = current_date.year

        # Parse the provided date string (e.g. "23 January")
        date_obj = datetime.strptime(date_str, "%d %B")

        # Check if the provided date has already passed this year
        if date_obj.replace(year=current_year) < current_date:
            # If the date has passed this year, assume the next year
            date_obj = date_obj.replace(year=current_year + 1)
        else:
            # Otherwise, use the current year
            date_obj = date_obj.replace(year=current_year)

        # Format the date in "DD/MM/YYYY" format
        return date_obj.strftime("%d/%m/%Y")
