import types

from bs4 import BeautifulSoup
from datetime import datetime
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

import json


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        json_data = json.loads(page.text)["Results"]

        for item in json_data["bin_collections_combined"]:
            soup = BeautifulSoup(list(item.values())[1], features="html.parser")
            soup.prettify()
            bin_text = soup.text.split(" ")
            try:
                bin_type = str.join(' ', bin_text[2:4]).strip().title()
                bin_date = datetime.strptime(str.join(' ', bin_text[-4:]).strip(), "%A %d %B %Y").strftime(date_format)

                if datetime.strptime(str.join(' ', bin_text[-4:]).strip(), "%A %d %B %Y").date() > \
                        datetime.now().date():
                    dict_data = {
                        "type":           bin_type,
                        "collectionDate": bin_date,
                    }
                    data["bins"].append(dict_data)

            except Exception:
                raise ValueError("Bin text has been changed, parser needs updating. Please open issue on GitHub.")

        return data
