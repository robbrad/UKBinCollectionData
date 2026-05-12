import requests
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://recyclingandrubbishcollections.camden.gov.uk/api"
COUNCIL_ID = "27"


def _match_property(properties, uprn=None, paon=None):
    """Match a property from search results by UPRN or house number/name."""
    if uprn:
        for prop in properties:
            if str(prop.get("uprn", "")) == str(uprn):
                return prop["id"]

    if paon:
        paon_norm = str(paon).strip().upper()
        # Exact start match (e.g. "12" matches "12 MABLEDON PLACE, ...")
        for prop in properties:
            name = str(prop.get("name", "")).upper()
            if name.startswith(paon_norm + " ") or name.startswith(paon_norm + ","):
                return prop["id"]
        # Contains match (e.g. "FLAT 3" matches "FLAT 3, 12 MABLEDON PLACE, ...")
        for prop in properties:
            name = str(prop.get("name", "")).upper()
            if paon_norm in name:
                return prop["id"]

    return properties[0]["id"]


class CouncilClass(AbstractGetBinDataClass):
    """
    Parser for London Borough of Camden Council
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)

        headers = {"Content-Type": "application/json"}

        # Step 1: Search by postcode to resolve property ID
        search_resp = requests.post(
            f"{BASE_URL}/getPropertySearch",
            json={"councilId": COUNCIL_ID, "searchQuery": user_postcode},
            headers=headers,
            timeout=30,
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()

        properties = search_data.get("data", [])
        if not properties:
            raise ValueError(f"No properties found for postcode: {user_postcode}")

        point_id = _match_property(properties, uprn=user_uprn, paon=user_paon)

        # Step 2: Get collection days
        collection_resp = requests.post(
            f"{BASE_URL}/getCollectionDays",
            json={
                "pointId": str(point_id),
                "pointType": "PointAddress",
                "councilId": COUNCIL_ID,
            },
            headers=headers,
            timeout=30,
        )
        collection_resp.raise_for_status()
        collection_data = collection_resp.json()

        data = {"bins": []}
        now = datetime.now()

        for service in collection_data.get("activeServices", []):
            bin_type = service.get("serviceName", "Unknown")

            for schedule in service.get("serviceSchedules", []):
                date_str = schedule.get("currentScheduledDate")
                if not date_str:
                    continue

                collection_date = datetime.fromisoformat(date_str)
                if collection_date.date() >= now.date():
                    data["bins"].append(
                        {
                            "type": bin_type,
                            "collectionDate": collection_date.strftime(date_format),
                        }
                    )

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
