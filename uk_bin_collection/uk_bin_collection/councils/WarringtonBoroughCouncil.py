import requests
from datetime import datetime

from uk_bin_collection.uk_bin_collection.common import check_uprn, date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.warrington.gov.uk/bin-collections",
}


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        uri = f"https://www.warrington.gov.uk/bin-collections/get-jobs/{user_uprn}"

        response = requests.get(uri, headers=HEADERS, timeout=30)
        response.raise_for_status()
        bin_collection = response.json()

        bindata = {"bins": []}
        schedule = bin_collection.get("schedule")
        if not isinstance(schedule, list):
            raise ValueError("Unexpected Warrington response: missing/invalid 'schedule'")

        for collection in schedule:
            bindata["bins"].append({
                "type": collection["Name"],
                "collectionDate": datetime.strptime(
                    collection["ScheduledStart"],
                    "%Y-%m-%dT%H:%M:%S",
                ).strftime(date_format),
            })

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )

        return bindata
