import json
from datetime import datetime

import requests
import urllib3

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        data = {"bins": []}
        current_month = datetime.today().strftime("%m")
        current_year = datetime.today().strftime("%Y")

        url = (
            f"https://mybins.blackburn.gov.uk/api/mybins/getbincollectiondays"
            f"?uprn={uprn}&month={current_month}&year={current_year}"
        )

        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
            verify=False,
            timeout=30,
        )
        response.raise_for_status()
        json_result = response.json()

        bin_collections = json_result.get("BinCollectionDays", [])
        for collection in bin_collections:
            if collection is None:
                continue
            entry = collection[0] if isinstance(collection, list) else collection
            bin_type = entry.get("BinType")
            current_collection_date = entry.get("CollectionDate")
            if not current_collection_date:
                continue
            current_dt = datetime.strptime(current_collection_date, "%Y-%m-%d")
            next_collection_date = entry.get("NextScheduledCollectionDate")

            if next_collection_date:
                next_dt = datetime.strptime(next_collection_date, "%Y-%m-%d")
                if datetime.today().date() <= current_dt.date() < next_dt.date():
                    collection_date = current_dt
                else:
                    collection_date = next_dt
            else:
                collection_date = current_dt

            data["bins"].append({
                "type": bin_type,
                "collectionDate": collection_date.strftime(date_format),
            })

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )
        return data
