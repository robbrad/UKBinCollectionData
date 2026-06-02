import json
import re
from datetime import datetime, timedelta

import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}

AREA = "CaerphillyCountyUK"
SERVICE = "50008"
SUGGEST_URL = f"https://api.eu.recollect.net/api/areas/{AREA}/services/{SERVICE}/address-suggest"
EVENTS_URL_TEMPLATE = (
    "https://api.eu.recollect.net/api/places/{place_id}/services/"
    + SERVICE
    + "/events"
)
CALENDAR_URL = (
    f"https://api.eu.recollect.net/api/areas/{AREA}/services/{SERVICE}"
    "/pages/en-GB/place_calendar.json"
)
WIDGET_CONFIG = {
    "area": AREA,
    "name": "calendar",
    "locale": "en-GB",
    "base": "https://api.eu.recollect.net",
    "place_cookie": f"rCw-{AREA}-waste",
    "client_cookie": f"rCc-{AREA}",
    "cookie_expires": 14,
    "third_party_cookie_enabled": 1,
    "place_not_found_in_guest": 0,
    "is_guest_service": 0,
}


def _resolve_place_id(postcode: str, paon: str) -> str:
    """Resolve postcode + house number to a ReCollect place_id.

    Caerphilly's ReCollect setup uses postcode-level qualifiers, not individual
    address parcels, in the address-suggest endpoint. To get per-address
    place_ids we must:
      1. Search the postcode to get a qualifier_id
      2. Call place_calendar with the qualifier to get the address picker
      3. Match the house number/name against the address list
    """
    # Step 1: Get qualifier from postcode
    params = {"q": postcode, "locale": "en-GB"}
    resp = requests.get(SUGGEST_URL, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    results = resp.json()

    # Some postcodes may return parcels directly
    parcels = [r for r in results if r.get("type") == "parcel" and r.get("place_id")]
    if parcels:
        return _match_parcel(parcels, paon)

    qualifiers = [r for r in results if r.get("type") == "place_qualifier"]
    if not qualifiers:
        raise ValueError(f"No results for postcode: {postcode}")

    qualifier_id = qualifiers[0]["qualifier_id"]

    # Step 2: Get address list from place_calendar using the qualifier
    cal_headers = {
        **HEADERS,
        "X-Recollect-Place": f"qualifier.{qualifier_id}:{SERVICE}",
    }
    cal_params = {"widget_config": json.dumps(WIDGET_CONFIG)}
    resp = requests.get(
        CALENDAR_URL, headers=cal_headers, params=cal_params, timeout=30
    )
    # 401 is expected here - the API returns address list with 401 status
    # when the qualifier needs to be narrowed to a specific address
    cal_data = resp.json()

    # Step 3: Extract addresses from the "Select your address" section
    addresses = []
    for section in cal_data.get("sections", []):
        for row in section.get("rows", []):
            if row.get("action") == "SET_PLACE" and row.get("place_id"):
                pid_full = row["place_id"]
                # place_id format: UUID:serviceId:areaName - extract UUID
                pid = pid_full.split(":")[0] if ":" in pid_full else pid_full
                addresses.append({"name": row.get("label", ""), "place_id": pid})

    if not addresses:
        raise ValueError(
            f"No addresses found for postcode {postcode} "
            f"(qualifier {qualifier_id})"
        )

    # Step 4: Match house number
    return _match_address(addresses, paon, postcode)


def _match_parcel(parcels: list, paon: str) -> str:
    """Match a house number/name against a list of parcel results."""
    if not paon:
        return parcels[0]["place_id"]

    paon_lower = paon.strip().lower()
    num_match = re.match(r"^(\d+[a-zA-Z]?)\b", paon_lower)

    for p in parcels:
        name = p.get("name", "").lower()
        if name.startswith(paon_lower):
            return p["place_id"]
        if num_match and name.startswith(num_match.group(1) + " "):
            return p["place_id"]

    # Fall back to first result
    return parcels[0]["place_id"]


def _match_address(addresses: list, paon: str, postcode: str) -> str:
    """Match a house number/name against the address list from place_calendar."""
    if not paon:
        return addresses[0]["place_id"]

    paon_clean = paon.strip()
    paon_lower = paon_clean.lower()
    num_match = re.match(r"^(\d+[a-zA-Z]?)\b", paon_clean)

    # Exact prefix match on label
    for addr in addresses:
        label = addr["name"].lower()
        if label.startswith(paon_lower):
            return addr["place_id"]

    # House number at start of label
    if num_match:
        house_num = num_match.group(1)
        for addr in addresses:
            label = addr["name"]
            if label.startswith(house_num + " "):
                return addr["place_id"]

    # Substring match (house name inside label)
    for addr in addresses:
        if paon_lower in addr["name"].lower():
            return addr["place_id"]

    # Fall back to first address with a warning
    return addresses[0]["place_id"]


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)
        check_paon(user_paon)

        place_id = _resolve_place_id(user_postcode, user_paon)

        now = datetime.now()
        after = now.strftime("%Y-%m-%d")
        before = (now + timedelta(days=60)).strftime("%Y-%m-%d")

        events_url = EVENTS_URL_TEMPLATE.format(place_id=place_id)
        params = {
            "nomerge": "1",
            "hide": "reminder_only",
            "after": after,
            "before": before,
            "locale": "en-GB",
        }
        response = requests.get(
            events_url, headers=HEADERS, params=params, timeout=60
        )
        response.raise_for_status()
        events_data = response.json()

        seen = set()
        for event in events_data.get("events", []):
            day = event.get("day")
            if not day:
                continue

            for flag in event.get("flags", []):
                if flag.get("event_type") != "pickup":
                    continue

                bin_type = flag.get("subject") or flag.get("name", "Unknown")
                collection_date = datetime.strptime(day, "%Y-%m-%d").strftime(
                    date_format
                )

                key = (bin_type, collection_date)
                if key not in seen:
                    seen.add(key)
                    data["bins"].append(
                        {
                            "type": bin_type,
                            "collectionDate": collection_date,
                        }
                    )

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
