#!/usr/bin/env python3

# This script pulls (in one hit) the data from
# Huntingdon District Council District Council Bins Data
from datetime import datetime

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

    def parse_data(self, page, **kwargs) -> None:

        try:
            user_uprn = kwargs.get("uprn")
            check_uprn(user_uprn)
            url = f"http://www.huntingdonshire.gov.uk/refuse-calendar/{user_uprn}"
            if not user_uprn:
                # This is a fallback for if the user stored a URL in old system. Ensures backwards compatibility.
                url = kwargs.get("url")
        except Exception as e:
            raise ValueError(f"Error getting identifier: {str(e)}")

        # Make a BS4 object
        page = requests.get(url)
        soup = BeautifulSoup(page.text, "html.parser")
        soup.prettify

        data = {"bins": []}

        no_garden_message = "Your property does not receive a garden waste collection"
        results = soup.find("ul", class_="d-print-none").find_all("li")

        for result in results:
            if no_garden_message in result.get_text(strip=True):
                continue
            else:
                text = result.get_text(strip=True)
                # Example: The next collection for your domestic waste in your 240lt wheeled bin is on
                before = "collection for your "
                after = " waste"
                # grab words in between
                bin_type = text[
                    text.index(before) + len(before) : text.index(after)
                ].capitalize()

                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": datetime.strptime(
                            result.find("strong").get_text(strip=True), "%A %d %B %Y"
                        ).strftime(date_format),
                    }
                )

        return data
