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

        URI = f"https://www.carmarthenshire.gov.wales/umbraco/Surface/SurfaceRecycling/Index/?uprn={user_uprn}&lang=en-GB"

        # Make the GET request
        response = requests.get(URI)

        # Parse the HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Find each bin collection container
        for container in soup.find_all(class_="bin-day-container"):
            # Get the bin type based on the class (e.g., Blue, Black, Garden, Nappy)
            bin_type = container.get("class")[1]  # Second class represents the bin type

            if bin_type == "Garden":
                continue

            # Find the next collection date
            date_tag = container.find(class_="font11 text-center")
            if date_tag:
                collection_date = date_tag.text.strip()
            else:
                continue

            dict_data = {
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    collection_date,
                    "%A %d/%m/%Y",
                ).strftime("%d/%m/%Y"),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
