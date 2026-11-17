"""Fetch Epping Forest collections from its AchieveService address lookup."""

from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from uk_bin_collection.uk_bin_collection.common import check_uprn, date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://eppingforestdc-self.achieveservice.com"
COLLECTION_URL = f"{BASE_URL}/en/service/Check_your_collection_day"


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)
        uprn = str(uprn).strip()
        if not uprn.isdigit() or len(uprn) > 12:
            raise ValueError("Epping Forest requires a valid property UPRN")

        # Reuse the anonymous session pattern used by Watford and East Herts.
        with requests.Session() as session:
            session.headers.update(
                {
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": f"{BASE_URL}/fillform/?iframe_id=fillform-frame-1&db_id=",
                }
            )
            response = session.get(
                f"{BASE_URL}/authapi/isauthenticated",
                params={
                    "uri": COLLECTION_URL,
                    "hostname": "eppingforestdc-self.achieveservice.com",
                    "withCredentials": "true",
                },
                timeout=20,
            )
            response.raise_for_status()
            sid = response.json().get("auth-session")
            if not sid:
                raise ValueError("Epping Forest did not provide a lookup session")
            response = session.post(
                f"{BASE_URL}/apibroker/runLookup",
                params={"id": "6651dfb99a74d", "sid": sid},
                json={"formValues": {"Section 1": {"LookupUPRN": {"value": uprn}}}},
                timeout=30,
            )
            response.raise_for_status()
            return parse_response(response.json())


def parse_response(payload: dict) -> dict:
    """Reject missing/stale results instead of manufacturing collection dates."""
    if payload.get("error") or payload.get("status") != "done":
        raise ValueError("Epping Forest collection lookup failed")
    rows = payload.get("integration", {}).get("transformed", {}).get("rows_data", {})
    row = rows.get("0") if isinstance(rows, dict) else None
    if not isinstance(row, dict):
        raise ValueError("Epping Forest returned no collection services")
    today = datetime.now(ZoneInfo("Europe/London")).date()
    bins = []
    # Keep existing bin names; item descriptions can instead mention batteries/WEEE.
    for service, label in (
        ("GeneralWaste", "Black Bin"),
        ("Recycling", "Blue Box and Recycling Sack"),
        ("FoodWaste", "Food Waste Bin"),
        ("GardenWaste", "Green-lidded Bin"),
    ):
        value = row.get(f"{service}ServiceNextCollection")
        if not value or value.startswith("0001-"):
            continue
        collection = datetime.fromisoformat(value).date()
        if collection < today:
            raise ValueError(f"Epping Forest returned a past {label} collection date")
        if service == "GardenWaste":
            end = row.get("GardenWasteServiceTo")
            if (
                end
                and not end.startswith("0001-")
                and datetime.fromisoformat(end).date() < today
            ):
                continue
        bins.append({"type": label, "collectionDate": collection.strftime(date_format)})
    if not bins:
        raise ValueError("Epping Forest returned no collection dates for this UPRN")
    bins.sort(key=lambda item: datetime.strptime(item["collectionDate"], date_format))
    return {"bins": bins}
