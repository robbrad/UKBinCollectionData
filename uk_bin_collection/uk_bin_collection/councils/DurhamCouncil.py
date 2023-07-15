import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        url = "https://www.durham.gov.uk/bincollections?uprn="
        uprn = kwargs.get("uprn")
        check_uprn(uprn)
        url += uprn
        requests.packages.urllib3.disable_warnings()
        page = requests.get(url)

        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")

        data = {}

        for bin_type in ["rubbish", "recycling", "gardenwaste"]:
            bin_info = soup.find(class_=f"bins{bin_type}")

            if bin_info:
                collection_text = bin_info.get_text(strip=True)

                if collection_text:
                    results = re.search("\\d\\d? [A-Za-z]+ \\d{4}", collection_text)
                    if results:
                        date = datetime.strptime(results[0], "%d %B %Y")
                        if date:
                            data[bin_type] = date.strftime("%Y-%m-%d")

        return data
