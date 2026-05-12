import re
from datetime import datetime, timedelta

import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}

AREA = "BassetlawUK"
SERVICE = "50015"


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        user_paon = kwargs.get("paon")
        postcode = kwargs.get("postcode")

        suggest_url = f"https://api.eu.recollect.net/api/areas/{AREA}/services/{SERVICE}/address-suggest"

        place_id = None

        # Strategy 1: Try paon as full address text (works if user passes "2 Albert Road")
        if user_paon and not user_paon.strip().isdigit():
            params = {"q": user_paon, "locale": "en-GB"}
            response = requests.get(suggest_url, headers=HEADERS, params=params, timeout=30)
            response.raise_for_status()
            for result in response.json():
                if result.get("type") == "parcel" and result.get("place_id"):
                    place_id = result["place_id"]
                    break

        # Strategy 2: Search postcode to get qualifier, then search house number within it
        if not place_id and postcode:
            params = {"q": postcode, "locale": "en-GB"}
            response = requests.get(suggest_url, headers=HEADERS, params=params, timeout=30)
            response.raise_for_status()
            results = response.json()

            # If postcode returns parcels directly, match by house number
            parcels = [r for r in results if r.get("type") == "parcel" and r.get("place_id")]
            if parcels:
                if user_paon:
                    for p in parcels:
                        name = p.get("name", "")
                        if name.lower().startswith(user_paon.lower()):
                            place_id = p["place_id"]
                            break
                if not place_id and parcels:
                    place_id = parcels[0]["place_id"]

            # If postcode returns qualifiers, get all addresses for that postcode
            if not place_id:
                qualifiers = [r for r in results if r.get("type") == "place_qualifier"]
                if qualifiers:
                    qual = qualifiers[0]
                    # Fetch all addresses in this postcode area
                    params2 = {"q": "", "locale": "en-GB", "place_qualifier_id": qual["qualifier_id"]}
                    response2 = requests.get(suggest_url, headers=HEADERS, params=params2, timeout=30)
                    response2.raise_for_status()
                    addresses = [r for r in response2.json() if r.get("type") == "parcel" and r.get("place_id")]

                    if not addresses:
                        # Qualifier empty search fails — try with postcode text inside qualifier
                        params3 = {"q": postcode, "locale": "en-GB", "place_qualifier_id": qual["qualifier_id"]}
                        response3 = requests.get(suggest_url, headers=HEADERS, params=params3, timeout=30)
                        response3.raise_for_status()
                        addresses = [r for r in response3.json() if r.get("type") == "parcel" and r.get("place_id")]

                    if addresses and user_paon:
                        for addr in addresses:
                            name = addr.get("name", "")
                            if name.lower().startswith(user_paon.lower()):
                                place_id = addr["place_id"]
                                break
                            # Match house number at start of address
                            num_match = re.match(r"^(\d+[a-zA-Z]?)\b", user_paon.strip())
                            if num_match and name.startswith(num_match.group(1) + " "):
                                place_id = addr["place_id"]
                                break

                    if not place_id and addresses:
                        place_id = addresses[0]["place_id"]

        # Strategy 3: Try combining paon + postcode as search
        if not place_id and user_paon and postcode:
            for q in [f"{user_paon} {postcode}", f"{user_paon}"]:
                params = {"q": q, "locale": "en-GB"}
                response = requests.get(suggest_url, headers=HEADERS, params=params, timeout=30)
                response.raise_for_status()
                for result in response.json():
                    if result.get("type") == "parcel" and result.get("place_id"):
                        place_id = result["place_id"]
                        break
                if place_id:
                    break

        if not place_id:
            raise ValueError(
                f"No address found for: {user_paon or postcode}"
            )

        now = datetime.now()
        after = now.strftime("%Y-%m-%d")
        before = (now + timedelta(days=60)).strftime("%Y-%m-%d")

        events_url = f"https://api.eu.recollect.net/api/places/{place_id}/services/{SERVICE}/events"
        params = {
            "nomerge": "1",
            "hide": "reminder_only",
            "after": after,
            "before": before,
            "locale": "en-GB",
        }
        response = requests.get(events_url, headers=HEADERS, params=params, timeout=60)
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
                collection_date = datetime.strptime(day, "%Y-%m-%d").strftime(date_format)

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
