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

        URI = f"https://bincollections.bromsgrove.gov.uk/BinCollections/Details?uprn={user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        # Parse the HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Find each collection container
        for container in soup.find_all(class_="collection-container"):
            # Get the bin type from the heading
            bin_type = container.find(class_="heading").text.strip()

            # Get the next collection date from the caption
            next_collection = (
                container.find(class_="caption")
                .text.replace("Next collection ", "")
                .strip()
            )

            dict_data = {
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    next_collection,
                    "%A, %d %B %Y",
                ).strftime("%d/%m/%Y"),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
