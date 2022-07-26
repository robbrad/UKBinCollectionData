#!/usr/bin/env python3

# This script pulls (in one hit) the data from
# Huntingdon District Council District Council Bins Data
from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page, **kwargs) -> None:
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        data = []

        BinTypes = ["Domestic", "Recycle", "Organic"]

        for i, date in enumerate(soup.find('ul', class_='d-print-none').find_all('li')):
            data.append({"BinType": BinTypes[i], "NextCollection": date.find('strong').get_text(strip=True)})
            ++i;

        return data
