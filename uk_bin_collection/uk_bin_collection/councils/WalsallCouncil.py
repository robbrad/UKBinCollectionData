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

        URI = f"https://cag.walsall.gov.uk/BinCollections/GetBins?uprn={user_uprn}"

        headers = {
            "user-agent": "Mozilla/5.0",
        }

        response = requests.get(URI, headers=headers)

        soup = BeautifulSoup(response.text, "html.parser")
        # Extract links to collection shedule pages and iterate through the pages
        schedule_links = soup.findAll("a", {"class": "nav-link"}, href=True)
        for item in schedule_links:
            if "roundname" in item["href"]:
                # get bin colour
                bincolour = item["href"].split("=")[-1].split("%")[0].upper()
                binURL = "https://cag.walsall.gov.uk" + item["href"]
                r = requests.get(binURL, headers=headers)
                soup = BeautifulSoup(r.text, "html.parser")
                table = soup.findAll("tr")
                for tr in table:
                    td = tr.findAll("td")
                    if td:
                        dict_data = {
                            "type": bincolour,
                            "collectionDate": datetime.strptime(
                                td[1].text.strip(), "%d/%m/%Y"
                            ).strftime("%d/%m/%Y"),
                        }
                        bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
