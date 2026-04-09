import requests
from datetime import datetime, timedelta

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        user_paon = kwargs.get("paon")
        postcode = kwargs.get("postcode")

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        }

        suggest_url = (
            "https://api.eu.recollect.net/api/areas/StirlingUK/services/waste/address-suggest"
        )

        # Build search queries to try, from most specific to least
        queries = []
        if user_paon:
            # Full address like "5, SUNNYLAW ROAD, BRIDGE OF ALLAN, STIRLING, FK9 4QA"
            # Try the full thing first
            queries.append(user_paon)
            # Then try just number + street (first two comma parts)
            parts = [p.strip() for p in user_paon.split(",")]
            if len(parts) >= 2:
                queries.append(f"{parts[0]} {parts[1]}")
            if len(parts) >= 1:
                queries.append(parts[0])
        if postcode:
            queries.append(postcode)

        place_id = None
        for query in queries:
            params = {"q": query, "locale": "en-GB"}
            response = requests.get(suggest_url, headers=headers, params=params, timeout=30)
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

        # Get collection events from the Recollect API
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
        response = requests.get(events_url, headers=headers, params=params, timeout=30)
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
