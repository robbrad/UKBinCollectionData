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

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-GB,en;q=0.9",
            "cache-control": "max-age=0",
            "dnt": "1",
            "priority": "u=0, i",
            "referer": "https://www.southampton.gov.uk",
            "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        }

        params = {
            "UPRN": {user_uprn},
        }

        r = requests.get(
            "https://www.southampton.gov.uk/whereilive/waste-calendar",
            params=params,
            headers=headers,
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
