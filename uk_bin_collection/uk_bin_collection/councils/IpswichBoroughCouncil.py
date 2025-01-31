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

    # Constants specific to IBC
    IBC_INCOMING_DATE_FORMAT = (
        r"\b(?:on\s+)?([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)? [A-Za-z]+ \d{4})\b"
    )

    IBC_SUPPORTED_BINS_METADATA = {
        "black": "General Waste",
        "blue": "Recycling Waste",
        "brown": "Garden Waste",
    }

            IBC_ENDPOINT = "https://app.ipswich.gov.uk/bin-collection/"

    

    def transform_date(self, date_str):
        date_str = re.sub(r"(st|nd|rd|th)", "", date_str)  # Remove ordinal suffixes
        date_obj = datetime.strptime(date_str, "%A %d %B %Y")
        return date_obj.strftime("%d/%m/%Y")

    def valid_poan(self, poan):
        # TODO the existing args from users don't encourage just street name as required; therefore may need a new OR manipulate an existing such as POAN
        return True

    def parse_data(self, page: str, **kwargs) -> dict:

        # user_paon = kwargs.get("paon") # TODO is the poan valid i.e. it appears to just be a street name?
        user_paon = "Ashdown Way"  # TODO test date, to be removed
        form_data = {"street-input": user_paon}

        response = requests.post(self.IBC_ENDPOINT, data=form_data, timeout=10)

        # Make a BS4 object
        soup = BeautifulSoup(response.content, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        div_section = soup.find("div", class_="ibc-page-content-section")

        if div_section:
            li_elements = div_section.find_all(
                "li"
            )  # li element exists for each day a bin or bins will be collected.

            date_pattern = re.compile(self.IBC_INCOMING_DATE_FORMAT)

            for li in li_elements:
                distinct_collection_info = li.get_text()
                date_match = date_pattern.search(distinct_collection_info)

                if date_match:
                    date = date_match.group(1)

                    for supported_bin in self.IBC_SUPPORTED_BINS_METADATA:
                        if supported_bin in distinct_collection_info:
                            # Transform the date from council format to expected UKBCD format
                            date_transformed = self.transform_date(date)

                            dict_data = {
                                "type": supported_bin.capitalize()
                                + " - "
                                + self.IBC_SUPPORTED_BINS_METADATA[supported_bin],
                                "collectionDate": date_transformed,
                            }

                            data["bins"].append(dict_data)
        return data
