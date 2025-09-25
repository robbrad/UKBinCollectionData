from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
import requests
from datetime import datetime


class CouncilClass(AbstractGetBinDataClass):
    """
    Rotherham collections via the public JSON API.
    Returns the same shape as before:
      {"bins": [{"type": "Black Bin", "collectionDate": "Tuesday, 29 September 2025"}, ...]}
    Accepts kwargs['premisesid'] (recommended) or a numeric kwargs['uprn'].
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # prefer explicit premisesid, fallback to uprn (if numeric)
        premises = kwargs.get("premisesid")
        uprn = kwargs.get("uprn")

        if uprn:
            # preserve original behaviour where check_uprn exists for validation,
            # but don't fail if uprn is intended as a simple premises id number.
            try:
                check_uprn(uprn)
            except Exception:
                # silently continue — user may have passed a numeric premises id as uprn
                pass

            if not premises and str(uprn).strip().isdigit():
                premises = str(uprn).strip()

        if not premises:
            raise ValueError("No premises ID supplied. Pass 'premisesid' in kwargs or a numeric 'uprn'.")

        api_url = "https://bins.azurewebsites.net/api/getcollections"
        params = {
            "premisesid": str(premises),
            "localauthority": kwargs.get("localauthority", "Rotherham"),
        }
        headers = {
            "User-Agent": "UKBinCollectionData/1.0 (+https://github.com/robbrad/UKBinCollectionData)"
        }

        try:
            resp = requests.get(api_url, params=params, headers=headers, timeout=10)
        except Exception as exc:
            print(f"Error contacting Rotherham API: {exc}")
            return {"bins": []}

        if resp.status_code != 200:
            print(f"Rotherham API request failed ({resp.status_code}). URL: {resp.url}")
            return {"bins": []}

        try:
            collections = resp.json()
        except ValueError:
            print("Rotherham API returned non-JSON response.")
            return {"bins": []}

        data = {"bins": []}
        seen = set()  # dedupe identical (type, date) pairs
        for item in collections:
            bin_type = item.get("BinType") or item.get("bintype") or "Unknown"
            date_str = item.get("CollectionDate") or item.get("collectionDate")
            if not date_str:
                continue

            # API gives ISO date like '2025-09-29' (or possibly '2025-09-29T00:00:00').
            try:
                iso_date = date_str.split("T")[0]
                parsed = datetime.strptime(iso_date, "%Y-%m-%d")
                formatted = parsed.strftime(date_format)
            except Exception:
                # skip malformed dates
                continue

            key = (bin_type.strip().lower(), formatted)
            if key in seen:
                continue
            seen.add(key)

            dict_data = {"type": bin_type.title(), "collectionDate": formatted}
            data["bins"].append(dict_data)

        if not data["bins"]:
            # helpful debugging note
            print(f"Rotherham API returned no collection entries for premisesid={premises}")

        return data