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
        bin_types = {"../images/bins/cal_blue.png":   "Mixed recycling",
                     "../images/bins/cal_green.png":  "General waste",
                     "../images/bins/cal_grey.png":   "Food waste",
                     "../images/bins/cal_brown.png":  "Organic waste",
                     "../images/bins/cal_purple.png": "Glass",
                     "../images/bins/cal_ash.png": "Ash bin"}

        # Find the page body with all the calendars
        body = soup.find("div", {"id": "printArticle"})
        cal_year = datetime.strptime(soup.select("#Year")[0].text.strip(), "%Y").year
        calendars = body.find_all_next("table", {"title": "Calendar"})

        # For each calendar grid, get the month and all icons within it. We only take icons with alt text, as this
        # includes the bin type while excluding spacers
        for item in calendars:
            cal_month = datetime.strptime(item.find_next("td").text.strip(), "%B").month
            icons = item.find_all("img", alt=True)

            # For each icon, get the day box, so we can parse the correct day number and make a datetime
            for icon in icons:
                cal_item = icon.find_parent().find_parent().find_parent().contents
                cal_day = datetime.strptime(cal_item[1].text.strip(), "%d").day
                bin_date = datetime(cal_year, cal_month, cal_day)

                # If the collection date is in the future, we want the date. Select the correct type, add the new
                # datetime, then add to the list
                if datetime.now() <= bin_date:
                    dict_data = {
                        "type":           bin_types.get(icon['src'].lower()),
                        "collectionDate": bin_date.strftime(date_format),
                    }
                    data["bins"].append(dict_data)

        return data
