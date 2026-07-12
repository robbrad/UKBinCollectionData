import re
from datetime import datetime

import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Fenland District Council — uses imactivate Bins API (Azure).
    No authentication required. Accepts postcode + house number.
    """

    API_BASE = "https://bins.azurewebsites.net/api"

    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        user_uprn = kwargs.get("uprn")

        if user_postcode:
            check_postcode(user_postcode)
        elif user_uprn:
            check_uprn(user_uprn)
        else:
            raise ValueError("Postcode or UPRN required")

        data = {"bins": []}

        premise_id = self._resolve_premise(user_postcode, user_paon, user_uprn)

        response = requests.get(
            f"{self.API_BASE}/getcollections",
            params={"premisesid": premise_id, "localauthority": "Fenland"},
            timeout=30,
        )
        response.raise_for_status()
        collections = response.json()

        for c in collections:
            bin_type = c.get("BinType", "")
            date_str = c.get("CollectionDate", "")
            if not bin_type or not date_str:
                continue
            data["bins"].append(
                {
                    "type": bin_type.title(),
                    "collectionDate": datetime.strptime(date_str, "%Y-%m-%d").strftime(
                        date_format
                    ),
                }
            )

        data["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )
        return data

    def _resolve_premise(self, postcode, paon, uprn):
        if not postcode:
            # Fenland has no national UPRN lookup - its API only knows its
            # own PremiseID. Users are guided (see project docs) to put
            # that PremiseID straight into the UPRN field, so use it
            # directly rather than requiring a postcode.
            if uprn:
                return uprn
            raise ValueError(
                "Postcode or PremiseID (as UPRN) required for Fenland lookup"
            )

        response = requests.get(
            f"{self.API_BASE}/getaddress",
            params={"postcode": postcode},
            timeout=30,
        )
        response.raise_for_status()
        addresses = response.json()

        if not addresses:
            raise ValueError(f"No addresses found for {postcode}")

        if len(addresses) == 1:
            return addresses[0]["PremiseID"]

        if paon:
            paon_upper = paon.upper().strip()
            for addr in addresses:
                addr_text = " ".join(
                    str(addr.get(f, "")).replace("\x00", "")
                    for f in ["Address1", "Address2", "Street"]
                ).upper()
                if addr_text.startswith(paon_upper) or paon_upper in addr_text:
                    return addr["PremiseID"]

        return addresses[0]["PremiseID"]
