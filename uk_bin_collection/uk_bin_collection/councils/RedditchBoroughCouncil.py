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

        URI = "https://bincollections.redditchbc.gov.uk/BinCollections/Details"

        data = {"UPRN": user_uprn}

        # Make the GET request
        response = requests.post(URI, data=data)

        # Parse the HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Find all collection containers
        collection_containers = soup.find_all("div", class_="collection-container")

        # Parse each collection container
        for container in collection_containers:
            # Extract bin type (from heading or image alt attribute)
            bin_type = container.find("img")["alt"]

            # Extract the next collection date (from the caption paragraph)
            next_collection = (
                container.find("p", class_="caption")
                .text.replace("Next collection ", "")
                .strip()
            )

            # Extract additional future collection dates (from the list items)
            future_dates = [li.text.strip() for li in container.find_all("li")]

            dict_data = {
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    next_collection,
                    "%A, %d %B %Y",
                ).strftime("%d/%m/%Y"),
            }
            bindata["bins"].append(dict_data)

            for date in future_dates:  # Add to the schedule
                dict_data = {
                    "type": bin_type,
                    "collectionDate": datetime.strptime(
                        date,
                        "%A, %d %B %Y",
                    ).strftime("%d/%m/%Y"),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
