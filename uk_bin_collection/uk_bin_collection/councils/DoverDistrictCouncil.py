from datetime import datetime, timezone

import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://portal.waste.dover.gov.uk/api"
COUNCIL_ID = "39"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "x-recaptcha-token": "",
}


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        postcode = kwargs.get("postcode")
        uprn = kwargs.get("uprn")
        paon = kwargs.get("paon") or kwargs.get("number")

        if postcode:
            check_postcode(postcode)

        point_id = self._resolve_point_id(postcode, uprn, paon)
        return self._get_collections(point_id)

    def _resolve_point_id(self, postcode, uprn, paon):
        search_query = postcode or uprn
        if not search_query:
            raise ValueError("Postcode or UPRN required")

        resp = requests.post(
            f"{BASE_URL}/getPropertySearch",
            json={"councilId": COUNCIL_ID, "searchQuery": search_query},
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])

        if not data:
            raise ValueError(f"No properties found for {search_query}")

        if uprn:
            for prop in data:
                if str(prop.get("uprn")) == str(uprn):
                    return str(prop["id"])

        if paon:
            paon_lower = paon.strip().lower()
            for prop in data:
                name = prop.get("name", "").lower()
                if name.startswith(paon_lower + " ") or name.startswith(paon_lower + ","):
                    return str(prop["id"])

        return str(data[0]["id"])

    def _get_collections(self, point_id):
        resp = requests.post(
            f"{BASE_URL}/getCollectionDays",
            json={
                "pointId": point_id,
                "pointType": "PointAddress",
                "councilId": COUNCIL_ID,
            },
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()

        now = datetime.now(timezone.utc)
        data = {"bins": []}

        for service in result.get("activeServices", []):
            service_name = service.get("serviceName", "")
            for schedule in service.get("serviceSchedules", []):
                date_str = schedule.get("currentScheduledDate")
                if not date_str:
                    continue
                dt = datetime.fromisoformat(date_str)
                if dt > now:
                    data["bins"].append(
                        {
                            "type": service_name,
                            "collectionDate": dt.strftime(date_format),
                        }
                    )

        data["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )
        return data
