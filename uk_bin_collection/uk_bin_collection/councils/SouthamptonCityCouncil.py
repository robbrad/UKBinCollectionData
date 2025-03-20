import time

import requests

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

        REGEX = r"(Glass|Recycling|General Waste|Garden Waste).*?([0-9]{1,2}\/[0-9]{1,2}\/[0-9]{4})"

        s = requests.Session()
        r = s.get(
            f"https://www.southampton.gov.uk/whereilive/waste-calendar?UPRN={user_uprn}"
        )
        r.raise_for_status()

        # Limit search scope to avoid duplicates
        calendar_view_only = re.search(
            r"#calendar1.*?listView", r.text, flags=re.DOTALL
        )[0]

        results = re.findall(REGEX, calendar_view_only)

        for item in results:

            dict_data = {
                "type": item[0],
                "collectionDate": datetime.strptime(item[1], "%m/%d/%Y").strftime(
                    "%d/%m/%Y"
                ),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
