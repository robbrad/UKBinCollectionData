import json
import requests
from datetime import datetime
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        url = f"https://api-2.tewkesbury.gov.uk/incab/rounds/{user_uprn}/next-collection"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        json_data = response.json()

        data = {"bins": []}

        # Legacy format: {"status":"OK","body":[{"collectionType":"...","NextCollection":"YYYY-MM-DD"}]}
        if isinstance(json_data, dict) and json_data.get("status") == "OK" and "body" in json_data:
            for entry in json_data["body"]:
                bin_type = entry.get("collectionType")
                date_str = entry.get("NextCollection")
                if bin_type and date_str:
                    try:
                        collection_date = datetime.strptime(date_str, "%Y-%m-%d")
                        data["bins"].append({
                            "type": bin_type,
                            "collectionDate": collection_date.strftime(date_format)
                        })
                    except ValueError:
                        continue
        # Current format: {"food":{"nextCollectionDate":"...Z"},"garden":{...},"recycling":{...},"refuse":{...}}
        elif isinstance(json_data, dict):
            type_map = {
                "refuse": "Refuse",
                "recycling": "Recycling",
                "garden": "Garden",
                "food": "Food",
            }
            for key, display_name in type_map.items():
                entry = json_data.get(key)
                if not isinstance(entry, dict):
                    continue
                date_str = entry.get("nextCollectionDate")
                if not date_str:
                    continue
                try:
                    # "2026-04-23T01:00:00.000Z"
                    collection_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    data["bins"].append({
                        "type": display_name,
                        "collectionDate": collection_date.strftime(date_format)
                    })
                except ValueError:
                    continue

        data["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )

        print(json.dumps(data, indent=2))
        return data
