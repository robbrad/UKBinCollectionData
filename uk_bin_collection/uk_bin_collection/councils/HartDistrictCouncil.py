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

        """
        Extracts bin types and their next collection dates for a given property UPRN.
        
        Retrieves the UPRN from kwargs (key "uprn"), validates it, requests the council's next-collection-dates endpoint, parses the returned HTML table rows, and returns a dictionary containing a list of bin entries. Each bin entry contains the bin type string and its collection date formatted as "DD/MM/YYYY".
        
        Parameters:
            page (str): Unused by this implementation; included for interface compatibility.
            uprn (str, in kwargs): Unique Property Reference Number used to query collection data.
        
        Returns:
            dict: A dictionary with a single key "bins" mapping to a list of objects of the form
                {"type": <str>, "collectionDate": "<DD/MM/YYYY>"}.
        """
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
            bin_types = row.find("td", class_="bin-service")

            bin_types = bin_types.text.split("&")

            collection_date = row.find("td", class_="bin-service-date")

            collection_date = self.format_date(collection_date.text.strip())

            for bin_type in bin_types:
                # Create a dictionary for each bin and append to the bins list
                bins.append(
                    {"type": bin_type.strip(), "collectionDate": collection_date}
                )

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