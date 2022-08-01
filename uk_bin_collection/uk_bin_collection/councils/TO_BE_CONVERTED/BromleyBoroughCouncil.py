#!/usr/bin/env python3

# This script pulls (in one hit) the data from
# Warick District Council Bins Data
from bs4 import BeautifulSoup
from get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str) -> dict:
        # Make a BS4 object
        soup = BeautifulSoup(page, features="html.parser")
        soup.prettify()

        data = {}

        for bins in soup.findAll("div", {"class": "govuk-grid-row"}):
            bin_type = bins.h3.text.strip()
            binCollection = bins.find("td", {"class": "next-service"})
            if (
                binCollection
            ):  # batteries don't have a service date or other info associated with them.
                data[bin_type] = binCollection.contents[-1].strip()

        return data
