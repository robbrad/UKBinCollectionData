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
        response = requests.get(
            f"https://map.erewash.gov.uk/isharelive.web/myerewash.aspx?action=SetAddress&UniqueId={uprn}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"},
        )

        soup = BeautifulSoup(response.text, features="html.parser")
        collections = soup.find("div", {"aria-label": "Waste Collection"}).find_all(
            "div", {"class": "atPanelContent"}
        )
        for c in collections:
            bin_type = c.find("h4").get_text(strip=True)
            if "my next" in bin_type.lower():
                collection_info = c.find("div", {"class": "atPanelData"}).get_text(
                    strip=True
                )
                results = re.search(
                    "([A-Za-z]+ \d+[A-Za-z]+ [A-Za-z]+ \d*)", collection_info
                )
                if results:
                    collection_date = datetime.strptime(
                        results[1]
                        .replace("th", "")
                        .replace("st", "")
                        .replace("nd", "")
                        .replace("rd", "")
                        .strip(),
                        "%A %d %B %Y",
                    ).strftime(date_format)
                    dict_data = {
                        "type": bin_type.replace("My Next ", "").replace(
                            " Collection", ""
                        ),
                        "collectionDate": collection_date,
                    }
                    data["bins"].append(dict_data)
                    if "garden waste" in collection_info.lower():
                        dict_data = {
                            "type": "Garden Waste",
                            "collectionDate": collection_date,
                        }
                        data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return data
