import time

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
        user_uprn = user_uprn.zfill(12)
        bindata = {"bins": []}

        URI = "https://www.argyll-bute.gov.uk/rubbish-and-recycling/household-waste/bin-collection"

        data = {"addressSelect": user_uprn}

        s = requests.session()
        r = s.post(URI, data=data)
        r.raise_for_status()

        soup = BeautifulSoup(r.content, features="html.parser")
        soup.prettify()

        # Find the table and extract the rows with bin schedule information
        table = soup.find("table", class_="table table-bordered")
        rows = table.find_all("tr")[1:]  # Skip the header row

        current_year = datetime.now().year
        # Loop through each row and extract the bin type and collection date
        for row in rows:
            cells = row.find_all("td")
            bin_type = cells[0].get_text(strip=True)
            collection_date = cells[1].get_text(strip=True)

            collection_date = datetime.strptime(
                collection_date,
                "%A %d %B",
            )

            if collection_date.month == 1:
                collection_date = collection_date.replace(year=current_year + 1)
            else:
                collection_date = collection_date.replace(year=current_year)

            dict_data = {
                "type": bin_type,
                "collectionDate": collection_date.strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
