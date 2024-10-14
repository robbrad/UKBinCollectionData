from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Parse the page
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        # Declare an empty dict for data, and pair icon source URLs with their respective bin type
        data = {"bins": []}
        bin_types = {
            "../Images/Bins/blueBin.gif": "Mixed recycling",
            "../Images/Bins/greenBin.gif": "General waste",
            "../Images/Bins/greyBin.gif": "Food waste",
            "../Images/Bins/brownBin.gif": "Organic waste",
            "../Images/Bins/purpleBin.gif": "Glass",
            "../Images/Bins/ashBin.gif": "Ash bin",
        }

        # Find the page body with all the calendars
        body = soup.find("div", {"id": "Application_ctl00"})
        calendars = body.find_all_next("table", {"title": "Calendar"})
        # For each calendar grid, get the month and all icons within it. We only take icons with alt text, as this
        # includes the bin type while excluding spacers
        for item in calendars:
            icons = item.find_all("img")
            # For each icon, get the day box, so we can parse the correct day number and make a datetime
            for icon in icons:
                cal_item = icon.find_parent().find_parent()
                bin_date = datetime.strptime(
                    cal_item["title"],
                    "%A, %d %B %Y",
                )

                # If the collection date is in the future, we want the date. Select the correct type, add the new
                # datetime, then add to the list
                if datetime.now() <= bin_date:
                    dict_data = {
                        "type": bin_types.get(icon["src"]),
                        "collectionDate": bin_date.strftime(date_format),
                    }
                    data["bins"].append(dict_data)

        return data
