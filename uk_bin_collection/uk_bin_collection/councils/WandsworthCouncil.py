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

        URI = f"https://www.wandsworth.gov.uk/my-property/?UPRN={user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        soup = BeautifulSoup(response.content, features="html.parser")
        soup.prettify()

        # Find all collection types
        collection_types = soup.find_all("h4", class_="collection-heading")

        # Iterate over each collection type
        for collection_type in collection_types:
            bin_types = collection_type.text.strip().split("/")
            collections = collection_type.find_next_sibling("div", class_="collections")

            # Extract next and previous collections
            next_collection = collections.find_all("div", class_="collection")

            # Parse each collection
            for collection in next_collection:
                # Extract the collection type (Next or Previous)
                strong_tag = collection.find("strong")
                collection_type = (
                    strong_tag.text.strip(":") if strong_tag else "Unknown"
                )

                # Extract the date
                date_text = (
                    strong_tag.next_sibling.strip()
                    if strong_tag and strong_tag.next_sibling
                    else "No date found"
                )

                if date_text == "No date found":
                    continue

                for bin_type in bin_types:
                    # Append to the schedule
                    dict_data = {
                        "type": bin_type,
                        "collectionDate": datetime.strptime(
                            date_text,
                            "%A %d %B %Y",
                        ).strftime(date_format),
                    }
                    bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
