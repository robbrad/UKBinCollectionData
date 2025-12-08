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

        URI = "https://selfserve.worcester.gov.uk/wccroundlookup/HandleSearchScreen"

        post_data = {
            "alAddrsel": user_uprn,
        }

        headers = {
            "referer": "https://selfserve.worcester.gov.uk/wccroundlookup/HandleSearchScreen",
            "content-type": "application/x-www-form-urlencoded",
        }

        response = requests.post(URI, data=post_data, headers=headers, verify=False)

        soup = BeautifulSoup(response.content, "html.parser")
        rows = soup.select("table.table tbody tr")

        for row in rows:
            bin_type = row.select_one("td:nth-of-type(2)").text.strip()
            collection_date = row.select_one("td:nth-of-type(3) strong").text.strip()

            # Skip if not applicable or if it's a sentence (not a date)
            if collection_date == "Not applicable":
                continue

            # Try to parse as date, skip if it fails (e.g., informational text)
            try:
                parsed_date = datetime.strptime(
                    collection_date,
                    "%A %d/%m/%Y",
                )
                dict_data = {
                    "type": bin_type,
                    "collectionDate": parsed_date.strftime("%d/%m/%Y"),
                }
                bindata["bins"].append(dict_data)
            except ValueError:
                # Skip entries that aren't valid dates (e.g., seasonal messages)
                continue

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
