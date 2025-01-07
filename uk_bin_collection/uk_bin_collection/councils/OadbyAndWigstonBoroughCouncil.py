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

        URI = f"https://my.oadby-wigston.gov.uk/location?put=ow{user_uprn}&rememberme=0&redirect=%2F"

        # Make the GET request
        response = requests.get(URI)

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        # Find the collection list
        collection_list = soup.find("ul", class_="refuse")

        current_year = datetime.now().year
        next_year = current_year + 1

        # Loop through each collection item
        for li in collection_list.find_all("li"):
            date_text = li.find("strong", class_="date").text.strip()
            bin_type = li.find("a").text  # Get the class for bin type

            # Parse the date
            if date_text == "Today":
                collection_date = datetime.now()
            else:
                try:
                    collection_date = datetime.strptime(date_text, "%A %d %b")
                except:
                    continue

            if (datetime.now().month == 12) and (collection_date.month == 1):
                collection_date = collection_date.replace(year=next_year)
            else:
                collection_date = collection_date.replace(year=current_year)

            dict_data = {
                "type": bin_type,
                "collectionDate": collection_date.strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
