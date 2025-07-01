import requests
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

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

        URI = f"https://www.newcastle-staffs.gov.uk/homepage/97/check-your-bin-day?uprn={user_uprn}"

        # Make the GET request
        request_headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(URI, headers=request_headers) 
        response.raise_for_status()
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        # Find the table
        table = soup.find("table", {"class": "data-table"})

        if table:
            rows = table.find("tbody").find_all("tr")
            for row in rows:
                date = datetime.strptime(
                    (
                        row.find_all("td")[0]
                        .get_text(strip=True)
                        .replace("Date:", "")
                        .strip()
                    ),
                    "%A %d %B",
                ).replace(year=datetime.now().year)
                if datetime.now().month > 10 and date.month < 3:
                    date = date + relativedelta(years=1)
                bin_types = (
                    row.find_all("td")[1]
                    .text.replace("Collection Type:", "")
                    .splitlines()
                )
                for bin_type in bin_types:
                    bin_type = bin_type.strip()
                    if bin_type:
                        dict_data = {
                            "type": bin_type.strip(),
                            "collectionDate": date.strftime("%d/%m/%Y"),
                        }
                        bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
