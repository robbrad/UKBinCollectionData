from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Get and check UPRN
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        uri = "https://www.rother.gov.uk/wp-admin/admin-ajax.php"
        params = {
            "action": "get_address_data",
            "uprn": user_uprn,
            "context": "full-page",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
        }

        # Send a POST request with form data and headers
        r = requests.post(uri, data=params, headers=headers, verify=False)

        result = r.json()

        if result["success"]:
            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(result["data"], "html.parser")
            soup.prettify()

            # print(soup)

            # Find the div elements with class "bindays-item"
            bin_days = soup.find_all("div", class_="bindays-item")

            # Loop through each bin item and extract type and date
            for bin_day in bin_days:
                # Extract bin type from the <h3> tag
                bin_type = bin_day.find("h3").get_text(strip=True).replace(":", "")

                # Extract date (or check if it's a subscription link for Garden Waste)
                date_span = bin_day.find("span", class_="find-my-nearest-bindays-date")
                if date_span:
                    if date_span.find("a"):
                        # If there is a link, this is the Garden bin signup link
                        continue
                    else:
                        # Otherwise, get the date text directly
                        date = date_span.get_text(strip=True)
                else:
                    date = None

                date = datetime.strptime(
                    remove_ordinal_indicator_from_date_string(date),
                    "%A %d %B",
                ).replace(year=datetime.now().year)
                if datetime.now().month == 12 and date.month == 1:
                    date = date + relativedelta(years=1)

                dict_data = {
                    "type": bin_type,
                    "collectionDate": date.strftime(date_format),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )
        return bindata
