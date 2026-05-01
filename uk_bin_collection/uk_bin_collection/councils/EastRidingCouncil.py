import requests
from datetime import datetime

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# East Riding API returns BlueDate, GreenDate, BrownDate fields.
# Map to human-readable bin type names.
BIN_DATE_FIELDS = {
    "BlueDate": "Blue Bin (Recycling)",
    "GreenDate": "Green Bin (General Waste)",
    "BrownDate": "Brown Bin (Garden Waste)",
}

API_URL = "https://wasterecyclingapi.eastriding.gov.uk/api/RecyclingData/CollectionsData"
API_KEY = "ekBWR8tSiv6qwMo31REEeTZ5FAiMNB"
API_LICENSEE = "BinCollectionWebTeam"


class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)

        # API expects postcode without spaces
        postcode_clean = user_postcode.replace(" ", "")

        params = {
            "APIKey": API_KEY,
            "Licensee": API_LICENSEE,
            "Postcode": postcode_clean,
        }

        response = requests.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        result = response.json()

        if not result.get("dataRetrieved"):
            raise ValueError(
                f"No data returned for postcode {user_postcode}: "
                f"{result.get('dataMessage', 'unknown error')}"
            )

        entries = result.get("dataReturned", [])
        if not entries:
            raise ValueError(f"No addresses found for postcode {user_postcode}")

        # Match the house number/name against the Address field.
        # The API provides HouseNameOrder (string, e.g. "14" or a house name)
        # and Address (full address string like "14 THE LEASES BEVERLEY HU17 8LG").
        matched = None
        if user_paon:
            paon_upper = user_paon.strip().upper()
            # Try exact match on HouseNameOrder first (most reliable)
            for entry in entries:
                house_name = (entry.get("HouseNameOrder") or "").strip().upper()
                if house_name == paon_upper:
                    matched = entry
                    break
            # Fall back to Address startswith
            if not matched:
                for entry in entries:
                    address = (entry.get("Address") or "").upper()
                    if address.startswith(paon_upper):
                        matched = entry
                        break
            # Fall back to Address contains
            if not matched:
                for entry in entries:
                    address = (entry.get("Address") or "").upper()
                    if paon_upper in address:
                        matched = entry
                        break
        else:
            # No paon provided — if only one result, use it; otherwise fail
            if len(entries) == 1:
                matched = entries[0]
            else:
                raise ValueError(
                    f"Multiple addresses found for postcode {user_postcode} "
                    f"but no house number (paon) provided to disambiguate. "
                    f"Found {len(entries)} entries."
                )

        if not matched:
            available = [e.get("Address", "?") for e in entries]
            raise ValueError(
                f"No address matched '{user_paon}' at postcode {user_postcode}. "
                f"Available: {available}"
            )

        # Extract bin collection dates from the matched entry
        for field, bin_type in BIN_DATE_FIELDS.items():
            date_str = matched.get(field)
            if not date_str:
                continue
            try:
                collection_date = datetime.strptime(
                    date_str, "%Y-%m-%dT%H:%M:%S"
                )
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )
            except (ValueError, TypeError):
                continue

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
