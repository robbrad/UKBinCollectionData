import requests
from datetime import datetime

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

API_BASE = "https://wasteservices.sheffield.gov.uk/api"
COUNCIL_ID = "1"


def _match_property(properties, uprn=None, paon=None):
    """Match a property from search results by UPRN or house number/name."""
    if uprn:
        for prop in properties:
            if str(prop.get("uprn", "")) == str(uprn):
                return prop["id"]

    if paon:
        paon_norm = str(paon).strip().upper()
        # Exact start match (e.g. "12" matches "12 ACACIA AVENUE, ...")
        for prop in properties:
            name = str(prop.get("name", "")).upper()
            if name.startswith(paon_norm + " ") or name.startswith(paon_norm + ","):
                return prop["id"]
        # Word-boundary match to avoid "2" matching "22"
        import re
        paon_re = re.compile(r"(?<!\w)" + re.escape(paon_norm) + r"(?!\w)")
        for prop in properties:
            name = str(prop.get("name", "")).upper()
            if paon_re.search(name):
                return prop["id"]

    if uprn or paon:
        raise ValueError(
            f"Property not found for UPRN={uprn} PAON={paon}"
        )
    return properties[0]["id"]


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        postcode = kwargs.get("postcode")
        paon = kwargs.get("paon")
        check_postcode(postcode)

        headers = {
            "Content-Type": "application/json",
            "Origin": "https://wasteservices.sheffield.gov.uk",
        }

        # Step 1: Search by postcode
        search_resp = requests.post(
            f"{API_BASE}/getPropertySearch",
            json={"councilId": COUNCIL_ID, "searchQuery": postcode},
            headers=headers,
            timeout=30,
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()

        properties = search_data.get("data", [])
        if not properties:
            raise ValueError(f"No properties found for postcode: {postcode}")

        point_id = _match_property(properties, uprn=uprn, paon=paon)

        # Step 2: Get collection days
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
        parse_failures = 0

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
                    parse_failures += 1
                    continue

        if not bindata["bins"] and parse_failures:
            raise ValueError(
                f"Failed to parse {parse_failures} collection date(s) and no valid dates found"
            )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
