import logging
import re

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

_LOGGER = logging.getLogger(__name__)


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

        def bin_name(heading):
            # The heading reads "Your next <Bin Name> collection", where
            # "Your next" and "collection" are visually-hidden spans added
            # for screen readers. Drop those by tag rather than slicing
            # words, so multi-word names like "Food Waste Caddy" survive.
            parts = [
                text
                for text in heading.find_all(string=True)
                if "visually-hidden" not in (text.parent.get("class") or [])
            ]
            name = " ".join(" ".join(parts).split())
            name = re.sub(r"^Your next\s+", "", name, flags=re.IGNORECASE)
            return re.sub(r"\s+collection$", "", name, flags=re.IGNORECASE)

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

        # Parse each collection card as a self-contained unit instead of
        # pairing two page-wide heading/date lists by index. That pairing
        # breaks as soon as one card doesn't carry a date: the calendar
        # download link reuses the heading class, and a bin with no
        # scheduled collection (e.g. Food Waste Caddy) shows a "Collected
        # every <day>" frequency instead. Either shifts every later bin onto
        # the wrong date and drops the final one.
        for heading in soup.find_all("h3", class_="bin-collection-tasks__heading"):
            card = heading.parent

            date_element = card.find("p", class_="bin-collection-tasks__date")
            if date_element is not None:
                # Parse against a concrete candidate year rather than
                # letting strptime default to 1900, which isn't a leap
                # year and would crash on a genuine 29 February date. If
                # this year isn't a leap year either, fall back to next
                # year directly instead of raising.
                day_month = solve(date_element.get_text(strip=True))
                try:
                    date = datetime.strptime(f"{day_month} {now.year}", "%d %B %Y")
                except ValueError:
                    date = datetime.strptime(f"{day_month} {now.year + 1}", "%d %B %Y")
                else:
                    if date.date() < now.date():
                        date = datetime.strptime(
                            f"{day_month} {now.year + 1}", "%d %B %Y"
                        )
            else:
                frequency_day = card.select_one(
                    "p.bin-collection-tasks__frequency strong"
                )
                if frequency_day is None:
                    # Not a bin card at all, e.g. the calendar download link.
                    continue

                weekday = frequency_day.get_text(strip=True).title()
                if weekday not in days_of_week:
                    _LOGGER.warning(
                        "Lichfield: unrecognized frequency text %r for %s",
                        weekday,
                        bin_name(heading),
                    )
                    continue

                days_until_collection = (days_of_week[weekday] - now.weekday()) % 7
                date = now + timedelta(days=days_until_collection)

            bint = bin_name(heading)

            # Preserve the existing Home Assistant entity identity. The old
            # parser exposed this card as "Food Waste" by taking two words
            # from the heading, so changing it here would create a second
            # sensor downstream.
            if bint == "Food Waste Caddy":
                bint = "Food Waste"

            dict_data = {
                "type": bint,
                "collectionDate": date.strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        return bindata
