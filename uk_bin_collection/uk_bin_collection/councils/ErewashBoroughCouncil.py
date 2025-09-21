import json

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

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        label_map = {
            "domestic-waste-collection-service": "Household Waste",
            "recycling-collection-service": "Recycling",
            "garden-waste-collection-service": "Garden Waste",
        }

        requests.packages.urllib3.disable_warnings()
        response = requests.get(
            f"https://www.erewash.gov.uk/bbd-whitespace/one-year-collection-dates-without-christmas?uprn={uprn}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"},
        )
        # Parse the JSON response
        payload = response.json()
        bin_collection = json.loads(payload) if isinstance(payload, str) else payload

        cd = next(
            i["settings"]["collection_dates"]
            for i in bin_collection
            if i.get("command") == "settings"
        )

        for month in cd.values():
            for e in month:
                d = e["date"]  # "YYYY-MM-DD"
                label = label_map.get(
                    e.get("service-identifier"),
                    e.get("service") or e.get("service-identifier"),
                )

                dict_data = {
                    "type": label,
                    "collectionDate": datetime.strptime(d, "%Y-%m-%d").strftime(
                        date_format
                    ),
                }
                data["bins"].append(dict_data)

        return data
