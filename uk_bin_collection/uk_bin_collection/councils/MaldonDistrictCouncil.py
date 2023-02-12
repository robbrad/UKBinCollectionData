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
        data = {"bins": []}
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        requests.packages.urllib3.disable_warnings()
        response = requests.get(f"https://maldon.suez.co.uk/maldon/ServiceSummary?uprn={uprn}", headers={"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"})
        if response.status_code != 200:
            raise ValueError("No bin data found for provided UPRN.")

        soup = BeautifulSoup(response.text, features="html.parser")
        collections = soup.find_all("div", {"class": "panel"})
        for c in collections:
            binType = c.find("div", {"class": "panel-heading"}).get_text(strip=True)
            lastCollectionDate = ""
            nextCollectionDate = ""
            rows = c.find("div", {"class": "panel-body"}).find_all("div", {"class": "row"})
            for row in rows:
                if row.find("strong").get_text(strip=True).lower() == "last collection":
                    lastCollectionDate = row.find("div", {"class": "col-sm-9"}).get_text(strip=True)
                if row.find("strong").get_text(strip=True).lower() == "next collection":
                    nextCollectionDate = row.find("div", {"class": "col-sm-9"}).get_text(strip=True)

            if nextCollectionDate != "":
                collection_data = {
                    "type": binType,
                    "nextCollectionDate": nextCollectionDate,
                }
                if lastCollectionDate != "":
                    collection_data["lastCollectionDate"] = lastCollectionDate
                data["bins"].append(collection_data)

        return data
