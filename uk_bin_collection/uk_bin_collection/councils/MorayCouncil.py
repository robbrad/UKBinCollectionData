import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Moray Council bin collection scraper.
    Parses the annual calendar view which encodes bin types as CSS classes
    on day divs within month containers.
    """

    # CSS class -> bin type mapping (from the calendar legend)
    BIN_TYPE_MAP = {
        "B": "Brown Bin",
        "O": "Glass Container",
        "G": "Green Bin",
        "P": "Purple Bin",
        "C": "Blue Bin",
    }

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        bindata = {"bins": []}

        user_uprn = str(user_uprn).zfill(8)
        year = datetime.today().year

        url = f"https://bindayfinder.moray.gov.uk/cal_{year}_view.php?id={user_uprn}"
        response = requests.get(url)

        if response.status_code != 200:
            return bindata

        soup = BeautifulSoup(response.text, "html.parser")
        today = datetime.today().date()

        # Month names for parsing
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]

        for month_container in soup.find_all("div", class_="month-container"):
            header = month_container.find("div", class_="month-header")
            if not header or not header.find("h2"):
                continue
            month_name = header.find("h2").text.strip()
            if month_name not in month_names:
                continue
            month_num = month_names.index(month_name) + 1

            days_container = month_container.find("div", class_="days-container")
            if not days_container:
                continue

            day_num = 0
            for day_div in days_container.find_all("div"):
                css_classes = day_div.get("class", [])

                # Skip blank days
                if "blank" in css_classes:
                    continue

                # Get the day number from the text
                day_text = day_div.text.strip()
                if not day_text or not day_text.isdigit():
                    continue
                day_num = int(day_text)

                # Check if this day has bin collection classes
                for css_class in css_classes:
                    if css_class in ("blank", "day-name", ""):
                        continue

                    # Each character in the CSS class represents a bin type
                    for char in css_class:
                        if char in self.BIN_TYPE_MAP:
                            try:
                                collection_date = datetime(year, month_num, day_num).date()
                                if collection_date >= today:
                                    bindata["bins"].append({
                                        "type": self.BIN_TYPE_MAP[char],
                                        "collectionDate": collection_date.strftime(date_format),
                                    })
                            except ValueError:
                                continue

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
