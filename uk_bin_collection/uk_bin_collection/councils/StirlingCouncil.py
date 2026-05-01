import re
import requests
from datetime import datetime, timedelta

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
}


def _extract_street_from_paon(paon):
    if not paon:
        return None
    stripped = re.sub(r"^\d+[a-zA-Z]?\s+", "", paon.strip())
    if stripped and stripped != paon.strip():
        return stripped
    if not paon.strip()[0].isdigit():
        return paon.strip()
    return None


def _build_queries(paon, postcode):
    """Build search queries from most specific to least."""
    queries = []
    if paon:
        street = _extract_street_from_paon(paon)
        if street:
            num_match = re.match(r"^(\d+[a-zA-Z]?)\b", paon.strip())
            if num_match:
                queries.append(f"{num_match.group(1)} {street}")
        queries.append(paon)
        parts = [p.strip() for p in paon.split(",")]
        if len(parts) >= 2:
            queries.append(f"{parts[0]} {parts[1]}")
        if len(parts) >= 1:
            queries.append(parts[0])

    if postcode:
        try:
            pc_clean = postcode.replace(" ", "")
            pc_resp = requests.get(
                f"https://api.postcodes.io/postcodes/{pc_clean}",
                headers=HEADERS, timeout=10,
            )
            if pc_resp.status_code == 200:
                pc_data = pc_resp.json()
                if pc_data.get("status") == 200 and pc_data.get("result"):
                    lat = pc_data["result"]["latitude"]
                    lng = pc_data["result"]["longitude"]
                    rev_resp = requests.get(
                        f"{NOMINATIM_URL}/reverse",
                        params={"lat": lat, "lon": lng, "format": "json", "addressdetails": 1},
                        headers=HEADERS, timeout=10,
                    )
                    if rev_resp.status_code == 200:
                        addr = rev_resp.json().get("address", {})
                        road = addr.get("road") or addr.get("street")
                        if road and paon:
                            num = re.match(r"^(\d+[a-zA-Z]?)\b", paon.strip())
                            if num:
                                queries.append(f"{num.group(1)} {road}")
                        if road:
                            queries.append(road)
        except Exception:
            pass

        queries.append(postcode)

    return queries


class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        user_paon = kwargs.get("paon")
        postcode = kwargs.get("postcode")

        suggest_url = (
            "https://api.eu.recollect.net/api/areas/StirlingUK/services/waste/address-suggest"
        )

        queries = _build_queries(user_paon, postcode)

        place_id = None
        for query in queries:
            params = {"q": query, "locale": "en-GB"}
            response = requests.get(suggest_url, headers=HEADERS, params=params, timeout=30)
            response.raise_for_status()
            results = response.json()

            for result in results:
                if result.get("type") == "parcel" and result.get("place_id"):
                    place_id = result["place_id"]
                    break
            if place_id:
                break

        if not place_id:
            raise ValueError(
                f"No specific address found for: {user_paon or postcode}. "
                f"Tried queries: {queries}"
            )

        now = datetime.now()
        after = now.strftime("%Y-%m-%d")
        before = (now + timedelta(days=60)).strftime("%Y-%m-%d")

        events_url = (
            "https://api.eu.recollect.net/api/areas/StirlingUK/services/waste/events"
        )
        params = {
            "nomerge": "1",
            "after": after,
            "before": before,
            "locale": "en-GB",
            "place_id": place_id,
        }
        response = requests.get(events_url, headers=HEADERS, params=params, timeout=30)
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
