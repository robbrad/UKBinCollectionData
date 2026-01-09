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

        URI1 = f"https://service.folkestone-hythe.gov.uk/webapp/myarea/?uprn={user_uprn}&tab=collections"
        URI2 = f"https://service.folkestone-hythe.gov.uk/webapp/myarea/api_collections.php?uprn={user_uprn}"

        # Make the GET request
        session = requests.session()
        response = session.get(
            URI1
        )  # Initialize session state (cookies) required by URI2
        response.raise_for_status()  # Validate session initialization
        response = session.get(URI2)
        response.raise_for_status()  # Raise HTTPError for bad status codes

        soup = BeautifulSoup(response.text, features="html.parser")

        collections = soup.find_all("article", {"class": "service-card"})
        for collection in collections:
            bin_type = collection.find("h3")
            if not bin_type:
                continue
            bin_type = bin_type.text
            next_collection = collection.find("p", {"class": "service-next"})
            if not next_collection or ":" not in next_collection.text:
                continue

            try:
                date_str = next_collection.text.split(":")[1].split("(")[0].strip()
                dt = datetime.strptime(date_str, "%A, %d %B %Y")
            except (ValueError, IndexError):
                continue

            dict_data = {
                "type": bin_type.strip(),
                "collectionDate": dt.strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
