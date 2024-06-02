from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    baseclass. They can also override some
    operations with a default implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        # Check the UPRN is valid
        check_uprn(uprn)

        # Request URL
        url = f"https://secure.sthelens.net/website/CollectionDates.nsf/servlet.xsp/NextCollections?source=1&refid={uprn}"

        # Make Request
        requests.packages.urllib3.disable_warnings()
        s = requests.Session()
        page = s.get(url)

        # Make a BS4 object
        soup = BeautifulSoup(
            re.sub("<div([^>]+)>", "", page.text).replace("</div>", ""),
            features="html.parser",
        )
        soup.prettify()

        data = {"bins": []}
        collection_rows = (
            soup.find("table", {"class": "multitable"}).find("tbody").find_all("tr")
        )

        for collection_row in collection_rows:
            # Get bin collection type
            bin_type = collection_row.find("th")
            if bin_type:
                bin_type = bin_type.get_text(strip=True)
                # Get bin collection dates
                for bin_date in collection_row.find_all("td"):
                    if bin_date.get_text(strip=True) != "Dates not allocated":
                        collection_date = datetime.strptime(
                            bin_date.get_text(strip=True), "%a %d %b %Y"
                        )
                        dict_data = {
                            "type": bin_type,
                            "collectionDate": collection_date.strftime(date_format),
                        }
                        data["bins"].append(dict_data)

        return data
