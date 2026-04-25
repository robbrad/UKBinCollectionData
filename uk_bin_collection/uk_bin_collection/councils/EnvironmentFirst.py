# Legacy script. Copied to Lewes and Eastbourne.

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
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}
        collect_div = soup.find("div", {"class": "collect"})
        if collect_div is None:
            return data

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
