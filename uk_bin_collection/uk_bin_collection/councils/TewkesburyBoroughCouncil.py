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
        response = requests.get(url)
        response.raise_for_status()

        json_data = response.json()

        data = {"bins": []}

        if json_data.get("status") == "OK" and "body" in json_data:
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

        # Sort by date
        data["bins"].sort(key=lambda x: x["collectionDate"])

        print(json.dumps(data, indent=2))
        return data