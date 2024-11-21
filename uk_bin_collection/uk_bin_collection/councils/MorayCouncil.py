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
        bindata = {"bins": []}

        user_uprn = user_uprn.zfill(8)

        year = datetime.today().year
        response = requests.get(
            f"https://bindayfinder.moray.gov.uk/cal_{year}_view.php",
            params={"id": user_uprn},
        )
        if response.status_code != 200:
            # fall back to known good calendar URL
            response = requests.get(
                "https://bindayfinder.moray.gov.uk/cal_2024_view.php",
                params={"id": user_uprn},
            )
        soup = BeautifulSoup(response.text, "html.parser")

        bin_types = {
            "G": "Green",
            "B": "Brown",
            "P": "Purple",
            "C": "Blue",
            "O": "Orange",
        }

        for month_container in soup.findAll("div", class_="month-container"):
            for div in month_container.findAll("div"):
                if "month-header" in div["class"]:
                    month = div.text
                elif div["class"] and div["class"][0] in ["B", "GPOC", "GBPOC"]:
                    bins = div["class"][0]
                    dom = int(div.text)
                    for i in bins:
                        dict_data = {
                            "type": bin_types.get(i),
                            "collectionDate": datetime.strptime(
                                f"{dom} {month} {year}",
                                "%d %B %Y",
                            ).strftime("%d/%m/%Y"),
                        }
                        bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
