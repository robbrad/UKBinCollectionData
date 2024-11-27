# This script pulls (in one hit) the data
# from Warick District Council Bins Data

from datetime import datetime

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
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        # Find all bin panels
        bin_panels = soup.find_all("div", class_="col-sm-4 col-lg-3")

        # Iterate through each panel to extract information
        for panel in bin_panels:
            bin_type = panel.find("img")["alt"].strip()

            waste_dates = panel.find(
                "div", class_="col-xs-12 text-center waste-dates margin-bottom-15"
            )

            for p in waste_dates.find_all("p")[1:]:
                date = p.text.strip()
                if " " in date:
                    date = date.split(" ")[1]

                dict_data = {
                    "type": bin_type,
                    "collectionDate": date,
                }
                data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
