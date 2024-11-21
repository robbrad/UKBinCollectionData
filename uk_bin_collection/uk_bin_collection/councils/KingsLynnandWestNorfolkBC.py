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
        user_uprn = user_uprn.zfill(12)
        bindata = {"bins": []}

        URI = "https://www.west-norfolk.gov.uk/info/20174/bins_and_recycling_collection_dates"

        headers = {"Cookie": f"bcklwn_uprn={user_uprn}"}

        # Make the GET request
        response = requests.get(URI, headers=headers)

        soup = BeautifulSoup(response.content, features="html.parser")
        soup.prettify()

        # Find all bin_date_container divs
        bin_date_containers = soup.find_all("div", class_="bin_date_container")

        # Loop through each bin_date_container
        for container in bin_date_containers:
            # Extract the collection date
            date = (
                container.find("h3", class_="collectiondate").text.strip().rstrip(":")
            )

            # Extract the bin type from the alt attribute of the img tag
            bin_type = container.find("img")["alt"]

            dict_data = {
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    date,
                    "%A %d %B %Y",
                ).strftime("%d/%m/%Y"),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
