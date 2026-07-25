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

        def bin_name(heading):
            # The heading reads "Your next Blue Bin collection", where the
            # "Your next" and "collection" wrappers are visually-hidden spans.
            # Dropping those leaves just the bin name, which keeps multi-word
            # names such as "Food Waste Caddy" intact.
            parts = [
                text
                for text in heading.find_all(string=True)
                if "visually-hidden" not in (text.parent.get("class") or [])
            ]
            name = " ".join(" ".join(parts).split())
            name = re.sub(r"^Your next\s+", "", name)
            return re.sub(r"\s+collection$", "", name)

        current_year = datetime.now().year
        current_month = datetime.now().month

        # Each bin is rendered in its own card. Pair the heading with the date
        # inside that same card rather than zipping two page-wide lists
        # together by index - not every card carries a date (a bin with no
        # scheduled collection shows a "collected every <day>" frequency
        # instead, and the calendar download link reuses the heading class),
        # so positional pairing silently shifts every bin onto the wrong date
        # and drops the last one entirely.
        for heading in soup.find_all("h3", class_="bin-collection-tasks__heading"):
            card = heading.parent
            date_element = card.find("p", class_="bin-collection-tasks__date")
            if date_element is None:
                continue

            bint = bin_name(heading)
            date = date_element.text.strip()

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
