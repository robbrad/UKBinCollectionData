# Lewes Borough Council uses the same script.

import re

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

        try:
            user_uprn = kwargs.get("uprn")
            check_uprn(user_uprn)
            url = f"https://environmentfirst.co.uk/house.php?uprn={user_uprn}"
            if not user_uprn:
                # Backwards compatibility for users who stored a URL.
                url = kwargs.get("url")
        except Exception as e:
            raise ValueError(f"Error getting identifier: {str(e)}")

        page = requests.get(url)
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}
        collect_div = soup.find("div", {"class": "collect"})
        if collect_div is None:
            return data

        # Site format (April 2026):
        #   <p class="address-line">...</p>
        #   <p>Your next rubbish collection day is: <strong>Tuesday 5th May 2026</strong></p>
        #   <p>Your next recycling collection day is: <strong>Tuesday 28th April 2026</strong></p>
        #   <p>Your next garden waste collection day is: <strong>Wednesday 6th May 2026</strong></p>
        # Some properties also have an introductory paragraph between the address
        # and the dates. Identify each row by the surrounding label rather than by
        # a fixed index — paragraph counts have shifted twice in 12 months.
        date_pattern = re.compile(
            r"(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})"
        )

        for p in collect_div.find_all("p"):
            strong = p.find("strong")
            if not strong:
                continue
            label = p.get_text(" ", strip=True).lower()
            if "rubbish" in label:
                bin_type = "Rubbish"
            elif "recycling" in label:
                bin_type = "Recycling"
            elif "garden" in label:
                bin_type = "Garden"
            else:
                continue
            match = date_pattern.search(strong.get_text(" ", strip=True))
            if not match:
                continue
            cleaned = remove_ordinal_indicator_from_date_string(match.group(1))
            try:
                collection_date = datetime.strptime(
                    cleaned, "%d %B %Y"
                ).strftime(date_format)
            except ValueError:
                continue
            data["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": collection_date,
                }
            )

        return data
