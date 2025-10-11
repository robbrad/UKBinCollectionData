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

        URI = f"https://www.eastdunbarton.gov.uk/services/a-z-of-services/bins-waste-and-recycling/bins-and-recycling/collections/?uprn={user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.find("table", {"class": "bin-table"})

        tbody = table.find("tbody")

        trs = tbody.find_all("tr")

        for tr in trs:
            tds = tr.find_all("td")
            bin_type = tds[0].get_text()
            collection_date_str = tds[1].find("span").get_text()

            collection_date = datetime.strptime(collection_date_str, "%A, %d %B %Y")

            dict_data = {
                "type": bin_type,
                "collectionDate": collection_date.strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
