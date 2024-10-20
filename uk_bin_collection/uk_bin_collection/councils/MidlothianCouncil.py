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
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(page.text, features="html.parser")

        # Initialize a dictionary to store the parsed bin data
        data = {"bins": []}

        # Define a mapping of bin collection labels to their corresponding types
        bin_types = {
            "Next recycling collection": "Recycling",
            "Next grey bin collection": "Grey Bin",
            "Next brown bin collection": "Brown Bin",
            "Next food bin collection": "Food Bin",
        }

        # Locate the <ul> element with the class "data-table"
        bin_collections = soup.find("ul", {"class": "data-table"})

        # Proceed only if the <ul> element is found
        if bin_collections:
            # Retrieve all <li> elements within the <ul>, skipping the first two (not relevant)
            bin_items = bin_collections.find_all("li")[2:]

            # Iterate through each bin item
            for bin in bin_items:
                bin_type = None
                # Retrieve the bin type from the header if it exists
                if bin.h2 and bin.h2.text.strip() in bin_types:
                    bin_type = bin_types[bin.h2.text.strip()]

                bin_collection_date = None
                # Retrieve the bin collection date from the div if it exists
                if bin.div and bin.div.text.strip():
                    try:
                        # Parse the collection date from the div text and format it
                        bin_collection_date = datetime.strptime(
                            bin.div.text.strip(),
                            "%A %d/%m/%Y",
                        ).strftime(date_format)
                    except ValueError:
                        # If date parsing fails, keep bin_collection_date as None
                        pass

                # If both bin type and collection date are identified, add to the data
                if bin_type and bin_collection_date:
                    data["bins"].append(
                        {
                            "type": bin_type,
                            "collectionDate": bin_collection_date,
                        }
                    )

        # Return the parsed data, which may be empty if no bins were found
        return data
