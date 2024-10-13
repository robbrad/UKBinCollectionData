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

        # Function to extract bin collection information
        def extract_bin_schedule(soup, heading_class):
            collections = []

            # Find the relevant section based on the heading class
            section_heading = soup.find("div", class_=heading_class)
            if section_heading:
                # Find all the bin collection dates in that section
                collection_dates = section_heading.find_next(
                    "div", class_="col-sm-12 col-md-9"
                ).find_all("h4")
                for date in collection_dates:
                    # Clean and add the date to the list
                    collections.append(date.get_text(strip=True))

            return collections

        # URL for bin collection schedule
        url = f"https://www.armaghbanbridgecraigavon.gov.uk/resident/binday-result/?address={user_uprn}"

        # Send a GET request to fetch the page content
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the page content using BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract bin collection schedules by their sections
            domestic_collections = extract_bin_schedule(soup, "heading bg-black")
            for collection in domestic_collections:
                bindata["bins"].append(
                    {"collectionDate": collection, "type": "Domestic"}
                )
            recycling_collections = extract_bin_schedule(soup, "heading bg-green")
            for collection in recycling_collections:
                bindata["bins"].append(
                    {"collectionDate": collection, "type": "Recycling"}
                )
            garden_collections = extract_bin_schedule(soup, "heading bg-brown")
            for collection in garden_collections:
                bindata["bins"].append({"collectionDate": collection, "type": "Garden"})

        else:
            print(f"Failed to retrieve data. Status code: {response.status_code}")

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
