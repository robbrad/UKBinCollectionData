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

        now = datetime.now()

        # Parse each collection card as a unit. Some cards, such as the weekly
        # food-waste service and the calendar download, do not contain an
        # explicit date. Pairing independent heading and date lists shifts all
        # subsequent dates onto the wrong bin when one of those cards appears.
        for task in soup.select("li.list__item"):
            heading = task.select_one("h3.bin-collection-tasks__heading")
            if heading is None:
                continue

            date_element = task.select_one("p.bin-collection-tasks__date")
            if date_element is not None:
                date = datetime.strptime(
                    solve(date_element.get_text(strip=True)), "%d %B"
                )
                date = date.replace(year=now.year)
                if date.date() < now.date():
                    date = date.replace(year=now.year + 1)
            else:
                frequency_day = task.select_one(
                    "p.bin-collection-tasks__frequency strong"
                )
                if frequency_day is None:
                    continue

                weekday = frequency_day.get_text(strip=True).title()
                if weekday not in days_of_week:
                    continue

                days_until_collection = (days_of_week[weekday] - now.weekday()) % 7
                date = now + timedelta(days=days_until_collection)

            heading_text = heading.get_text(" ", strip=True)
            bint = re.sub(
                r"^Your next\s+|\s+collection$", "", heading_text, flags=re.IGNORECASE
            )

            # Preserve the existing Home Assistant entity identity. The old
            # parser exposed this card as "Food Waste" by taking two words from
            # the heading, so changing it would create a second sensor.
            if bint == "Food Waste Caddy":
                bint = "Food Waste"

            dict_data = {
                "type": bint,
                "collectionDate": date.strftime("%d/%m/%Y"),
            }
            bindata["bins"].append(dict_data)

        return bindata
