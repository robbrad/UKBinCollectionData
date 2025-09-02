import re

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

        def solve(s):
            return re.sub(r"(\d)(st|nd|rd|th)", r"\1", s)

        headers = {
            "Origin": "https://www.lichfielddc.gov.uk",
            "Referer": "https://www.lichfielddc.gov.uk",
            "User-Agent": "Mozilla/5.0",
        }

        URI = f"https://www.lichfielddc.gov.uk/homepage/6/bin-collection-dates?uprn={user_uprn}"

        # Make the GET request
        response = requests.get(URI, headers=headers)

        soup = BeautifulSoup(response.text, "html.parser")

        bins = soup.find_all("h3", class_="bin-collection-tasks__heading")
        dates = soup.find_all("p", class_="bin-collection-tasks__date")

        current_year = datetime.now().year
        current_month = datetime.now().month

        for i in range(len(dates)):
            bint = " ".join(bins[i].text.split()[2:4])
            date = dates[i].text

            date = datetime.strptime(
                solve(date),
                "%d %B",
            )

            if (current_month > 10) and (date.month < 3):
                date = date.replace(year=(current_year + 1))
            else:
                date = date.replace(year=current_year)

            dict_data = {
                "type": bint,
                "collectionDate": date.strftime("%d/%m/%Y"),
            }
            bindata["bins"].append(dict_data)

        return bindata
