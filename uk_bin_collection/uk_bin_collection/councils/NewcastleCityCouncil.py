import re
from datetime import datetime, timedelta

import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# Newcastle retired the old community.newcastle.gov.uk AJAX endpoint in
# favour of a ReCollect widget (https://new.newcastle.gov.uk/recycling-waste/check-your-bin-collection-day).

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

AREA = "NewcastleUponTyneUK"
SERVICE = "50007"
SUGGEST_URL = (
    f"https://api.eu.recollect.net/api/areas/{AREA}/services/{SERVICE}/address-suggest"
)


def _normalise(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", str(text).upper()).strip()


def _suggest(q: str, **extra) -> list:
    params = {"q": q, "locale": "en-GB", **extra}
    response = requests.get(SUGGEST_URL, headers=HEADERS, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def _parcels(results: list) -> list:
    return [r for r in results if r.get("type") == "parcel" and r.get("place_id")]


def _starts_with_paon(name: str, paon: str) -> bool:
    # Word-boundary prefix match so "1" does not match "10 Some Street"
    return re.match(rf"{re.escape(_normalise(paon))}\b", _normalise(name)) is not None


def _pick(parcels: list, paon: str, postcode: str):
    """Pick the parcel matching the paon (and postcode, when given)."""
    if paon:
        parcels = [p for p in parcels if _starts_with_paon(p.get("name", ""), paon)]
    if postcode:
        pc = _normalise(postcode)
        in_postcode = [
            p for p in parcels if _normalise(p.get("name", "")).endswith(pc)
        ]
        if in_postcode:
            parcels = in_postcode
        elif paon:
            return None
    return parcels[0]["place_id"] if parcels else None


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        user_paon = kwargs.get("paon") or kwargs.get("house_number")
        postcode = kwargs.get("postcode")

        if user_paon and postcode:
            user_paon = re.sub(
                r",?\s*" + re.escape(postcode) + r"\s*$", "", user_paon, flags=re.I
            ).strip()

        place_id = None

        # ReCollect's address search is a prefix match on "<number> <street>, <town>",
        # so a full address with extra locality parts ("..., Gosforth, Newcastle upon
        # Tyne") finds nothing. Try the address, then progressively shorter comma prefixes.
        if user_paon and not user_paon.strip().isdigit():
            parts = [p.strip() for p in user_paon.split(",") if p.strip()]
            if len(parts) > 1 and parts[0].isdigit():
                # "1, Some Street, Town" -> "1 Some Street, Town"
                parts = [f"{parts[0]} {parts[1]}"] + parts[2:]
            candidates = [", ".join(parts[:i]) for i in range(len(parts), 0, -1)]
            for q in candidates:
                place_id = _pick(_parcels(_suggest(q)), q, postcode)
                if place_id:
                    break

        if not place_id and postcode:
            results = _suggest(postcode)
            parcels = _parcels(results)
            if parcels:
                if user_paon:
                    place_id = _pick(parcels, user_paon, None)
                elif len(parcels) == 1:
                    place_id = parcels[0]["place_id"]

            if not place_id and user_paon:
                qualifiers = [r for r in results if r.get("type") == "place_qualifier"]
                if qualifiers:
                    addresses = _parcels(
                        _suggest(
                            f"{user_paon} {postcode}",
                            place_qualifier_id=qualifiers[0]["qualifier_id"],
                        )
                    )
                    place_id = _pick(addresses, user_paon, None)

        if not place_id and user_paon and postcode:
            for q in [f"{user_paon} {postcode}", user_paon]:
                place_id = _pick(_parcels(_suggest(q)), user_paon, postcode)
                if place_id:
                    break

        if not place_id:
            raise ValueError(
                f"No address found for: {user_paon or postcode}. "
                "Newcastle's address search needs the house number and street name."
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

        if not data["bins"]:
            raise ValueError("No collections found for this address")

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
