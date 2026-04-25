from datetime import datetime

import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import (
    AbstractGetBinDataClass,
)


class CouncilClass(AbstractGetBinDataClass):
    """
    Rotherham collections via Imactivate's shared `bins.azurewebsites.net` API.
    Rotherham's own bin-day page directs residents to a printed PDF calendar
    only — there is no usable web lookup at rotherham.gov.uk. The same data
    backs the Rotherham Bins Android app and is exposed on the Imactivate
    shared instance keyed by PremiseID + LocalAuthority.

    Resolution order:
        1. explicit `premisesid` kwarg (Imactivate ID, NOT a UPRN)
        2. `postcode` + `paon` resolved through getaddress
        3. numeric `uprn` only if it is in fact an Imactivate PremiseID
           (kept for backward compatibility with old configs — most UPRNs
           will yield no collections from this endpoint)
    """

    BASE = "https://bins.azurewebsites.net/api"
    LA = "Rotherham"
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    )

    def _resolve_premise(self, postcode: str, paon: str) -> str:
        params = {"postcode": postcode, "localauthority": self.LA}
        r = requests.get(
            f"{self.BASE}/getaddress",
            params=params,
            headers={"User-Agent": self.UA},
            timeout=15,
        )
        r.raise_for_status()
        rows = r.json() or []

        target = str(paon).strip().lower()
        if not target:
            if not rows:
                raise ValueError(
                    f"No addresses found for postcode {postcode}"
                )
            return str(rows[0].get("PremiseID"))

        # Match against Address2 (house number/name) first, then Street.
        for row in rows:
            for key in ("Address2", "Address1", "Street"):
                value = row.get(key)
                if value is None:
                    continue
                if str(value).strip().lower() == target:
                    return str(row.get("PremiseID"))

        # Looser substring fallback so addresses like "Flat 3, 22A" match
        # against a paon of "22A".
        for row in rows:
            blob = " ".join(
                str(row.get(k, "")).strip()
                for k in ("Address1", "Address2", "Street")
            ).lower()
            if target and target in blob:
                return str(row.get("PremiseID"))

        raise ValueError(
            f"No address matching '{paon}' for postcode {postcode}"
        )

    def parse_data(self, page: str, **kwargs) -> dict:
        premises = kwargs.get("premisesid")

        if not premises:
            postcode = kwargs.get("postcode")
            paon = kwargs.get("paon")
            if postcode:
                check_postcode(postcode)
                premises = self._resolve_premise(postcode, paon or "")

        if not premises:
            uprn = kwargs.get("uprn")
            if uprn and str(uprn).strip().isdigit():
                premises = str(uprn).strip()

        if not premises:
            raise ValueError(
                "Rotherham requires either an Imactivate `premisesid` or a "
                "`postcode` (plus optionally `paon`) to resolve one."
            )

        params = {"premisesid": str(premises), "localauthority": self.LA}
        try:
            resp = requests.get(
                f"{self.BASE}/getcollections",
                params=params,
                headers={"User-Agent": self.UA},
                timeout=15,
            )
        except Exception as exc:
            print(f"Error contacting Rotherham API: {exc}")
            return {"bins": []}

        if resp.status_code != 200:
            print(
                f"Rotherham API request failed ({resp.status_code}). "
                f"URL: {resp.url}"
            )
            return {"bins": []}

        try:
            collections = resp.json() or []
        except ValueError:
            print("Rotherham API returned non-JSON response.")
            return {"bins": []}

        data = {"bins": []}
        seen = set()
        for item in collections:
            bin_type = (
                item.get("BinType") or item.get("bintype") or "Unknown"
            )
            date_str = (
                item.get("CollectionDate") or item.get("collectionDate")
            )
            if not date_str:
                continue
            try:
                iso_date = date_str.split("T")[0]
                parsed = datetime.strptime(iso_date, "%Y-%m-%d")
                formatted = parsed.strftime(date_format)
            except Exception:
                continue
            key = (bin_type.strip().lower(), formatted)
            if key in seen:
                continue
            seen.add(key)
            data["bins"].append(
                {"type": bin_type, "collectionDate": formatted}
            )

        data["bins"].sort(
            key=lambda x: datetime.strptime(
                x["collectionDate"], date_format
            )
        )
        return data
