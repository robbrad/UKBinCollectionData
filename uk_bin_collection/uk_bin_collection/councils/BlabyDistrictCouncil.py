import requests
from bs4 import BeautifulSoup
import urllib3

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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

        URI = f"https://my.blaby.gov.uk/set-location.php?ref={user_uprn}&redirect=collections"

        # Make the GET request (User-Agent required to avoid 403)
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        })
        response = session.get(URI, verify=False, timeout=30)
        response.raise_for_status()

        # Parse the HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Find each collection container based on the class "box-item"
        for container in soup.find_all(class_="box-item"):

            # Get the next collection dates from the <p> tag containing <strong>
            try:
                dates_tag = (
                    container.find("p", string=lambda text: "Next" in text)
                    .find_next("p")
                    .find("strong")
                )
            except:
                continue
            collection_dates = (
                dates_tag.text.strip().split(", and then ")
                if dates_tag
                else "No dates found"
            )

            for collection_date in collection_dates:
                dict_data = {
                    "type": container.find("h2").text.strip(),
                    "collectionDate": collection_date,
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
