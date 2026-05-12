import requests
from datetime import datetime

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

API_BASE = "https://wasteservices.sheffield.gov.uk/api"
COUNCIL_ID = "1"


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        postcode = kwargs.get("postcode")

        if not uprn:
            raise ValueError("UPRN is required for Sheffield")

        headers = {
            "Content-Type": "application/json",
            "Origin": "https://wasteservices.sheffield.gov.uk",
        }

        point_id = None

        if postcode:
            search_resp = requests.post(
                f"{API_BASE}/getPropertySearch",
                json={"councilId": COUNCIL_ID, "searchQuery": postcode},
                headers=headers,
                timeout=30,
            )
            search_resp.raise_for_status()
            search_data = search_resp.json()

            for prop in search_data.get("data", []):
                if str(prop.get("uprn")) == str(uprn):
                    point_id = prop["id"]
                    break

        if not point_id:
            search_resp = requests.post(
                f"{API_BASE}/getPropertySearch",
                json={"councilId": COUNCIL_ID, "searchQuery": str(uprn)},
                headers=headers,
                timeout=30,
            )
            search_resp.raise_for_status()
            search_data = search_resp.json()

            for prop in search_data.get("data", []):
                if str(prop.get("uprn")) == str(uprn):
                    point_id = prop["id"]
                    break

        if not point_id:
            raise ValueError(f"Could not find property for UPRN {uprn}")

        collection_resp = requests.post(
            f"{API_BASE}/getCollectionDays",
            json={
                "pointId": point_id,
                "pointType": "PointAddress",
                "councilId": COUNCIL_ID,
            },
            headers=headers,
            timeout=30,
        )
        collection_resp.raise_for_status()
        collection_data = collection_resp.json()

        bindata = {"bins": []}

        for service in collection_data.get("activeServices", []):
            bin_type = service.get("serviceName", "Unknown")
            for schedule in service.get("serviceSchedules", []):
                if schedule.get("state") == "Complete":
                    continue
                date_str = schedule.get("currentScheduledDate") or schedule.get(
                    "originalScheduledDate"
                )
                if not date_str:
                    continue
                try:
                    dt = datetime.fromisoformat(date_str)
                    bindata["bins"].append(
                        {
                            "type": bin_type,
                            "collectionDate": dt.strftime(date_format),
                        }
                    )
                except (ValueError, TypeError):
                    continue

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
