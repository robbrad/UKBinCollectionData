import requests
from bs4 import BeautifulSoup, Tag

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

        URI = f"https://diogel.gwynedd.llyw.cymru/Daearyddol/en/LleDwinByw/Index/{user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        soup = BeautifulSoup(response.text, "html.parser")
        collections_headline = soup.find("h6", text="Next collection dates:")
        if not isinstance(collections_headline, Tag):
            raise Exception("Could not find collections")
        collections = collections_headline.find_next("ul").find_all("li")

        for collection in collections:
            if not isinstance(collection, Tag):
                continue
            for p in collection.find_all("p"):
                p.extract()

            bin_type, date_str = collection.text.strip().split(":")[:2]
            bin_type, date_str = bin_type.strip(), date_str.strip()

            dict_data = {
                "type": bin_type,
                "collectionDate": datetime.strptime(date_str, "%A %d/%m/%Y").strftime(
                    date_format
                ),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
