from datetime import date, datetime

import requests

from uk_bin_collection.uk_bin_collection.common import date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://www.orkney.gov.uk/actions/_orkney"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
    ),
}


def _parse_collections(payload: dict, today: date) -> dict:
    area = payload.get("binCollectionArea") or {}
    labels = {k: v.get("label", k) for k, v in (payload.get("binConfig") or {}).items()}
    bins = []
    for key, events in area.items():
        if not isinstance(events, list):
            continue  # e.g. "area": "Area 3"
        for event in events:
            collection = datetime.strptime(event["date"], "%Y-%m-%d").date()
            if collection >= today:
                bins.append(
                    {
                        "type": labels.get(key, key.replace("_", " ").title()),
                        "collectionDate": collection.strftime(date_format),
                    }
                )
    bins.sort(key=lambda b: datetime.strptime(b["collectionDate"], date_format))
    return {"bins": bins}


class CouncilClass(AbstractGetBinDataClass):
    """
    Orkney's relaunched website looks collections up by address: a search
    endpoint returns address IDs (UPRNs) and a lookup endpoint returns the
    collection area's dated schedule. Schedules are per collection area, so
    any address on the same street gives the same dates.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_paon = kwargs.get("paon")
        session = requests.Session()
        session.headers.update(HEADERS)

        if user_uprn:
            address_id = str(user_uprn).strip()
        elif user_paon:
            resp = session.get(
                f"{BASE_URL}/address/search", params={"q": user_paon}, timeout=30
            )
            resp.raise_for_status()
            addresses = resp.json().get("addresses") or []
            if not addresses:
                raise ValueError(
                    f"No Orkney address found for '{user_paon}'. Try your house "
                    "number and street, e.g. '1 Albert Street, Kirkwall'."
                )
            address_id = addresses[0]["addressId"]
        else:
            raise ValueError(
                "Provide your address or street (house number parameter) or UPRN."
            )

        resp = session.get(
            f"{BASE_URL}/bin-collection/lookup-address",
            params={"addressId": address_id},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("success"):
            raise ValueError(
                f"Orkney's bin lookup failed for address ID {address_id}: "
                f"{payload.get('error') or payload}"
            )
        return _parse_collections(payload, datetime.now().date())
