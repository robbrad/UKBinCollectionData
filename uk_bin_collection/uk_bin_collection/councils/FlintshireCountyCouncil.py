import requests
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
        bindata = {"bins": []}

        URI = f"https://digital.flintshire.gov.uk/FCC_BinDay/Home/Details2/{user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        # Parse the HTML content
        soup = BeautifulSoup(response.content, "html.parser")

        # Adjust these tags and classes based on actual structure
        # Example for finding collection dates and types
        bin_collections = soup.find_all(
            "div", class_="col-md-12 col-lg-12 col-sm-12 col-xs-12"
        )  # Replace with actual class name

        # Extracting and printing the schedule data
        schedule = []
        for collection in bin_collections:
            dates = collection.find_all("div", class_="col-lg-2 col-md-2 col-sm-2")
            bin_type = collection.find("div", class_="col-lg-3 col-md-3 col-sm-3")

            if dates[0].text.strip() == "Date of Collection":
                continue

            bin_types = bin_type.text.strip().split(" / ")
            date = dates[0].text.strip()

            # Loop through the dates for each collection type
            for bin_type in bin_types:

                dict_data = {
                    "type": bin_type,
                    "collectionDate": date,
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )
        return bindata
