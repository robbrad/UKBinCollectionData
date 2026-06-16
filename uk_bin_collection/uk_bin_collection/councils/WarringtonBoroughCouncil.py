import requests
from datetime import datetime

from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinData

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.warrington.gov.uk/bin-collections",
}


class CouncilClass(AbstractGetBinData):
    def parse_data(self, page, **kwargs):
        url = kwargs.get("url")

        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()

        bins = {
            "green": "Green",
            "blue": "Blue",
            "foodwaste": "Food Waste",
            "black": "Black",
        }

        entries = []

        for key, label in bins.items():
            timestamp = data.get(key)
            if not timestamp:
                continue

            entries.append({
                "type": label,
                "collectionDate": datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y"),
            })

        return entries
