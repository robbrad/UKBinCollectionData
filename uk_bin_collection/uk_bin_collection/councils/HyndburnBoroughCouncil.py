import json
import re
from datetime import datetime

import requests
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# iTouchVision iApp. The React front end at iapp.itouchvision.com calls these
# JSON endpoints with an AES-CBC encrypted query in the P_PARAMETER header and
# returns an AES-CBC encrypted hex body. Key/IV are static in the public JS
# bundle (same values as NewportCityCouncil).
API_URL = "https://itouchvision.app/portal/itouchvision/"
HYNDBURN_UUID = "FEBA68993831481FD81B2E605364D00A8DC017A4"
KEY_HEX = "F57E76482EE3DC3336495DEDEEF3962671B054FE353E815145E29C5689F72FEC"
IV_HEX = "2CBF4FC35C69B82362D393A4F0B9971A"


def _encrypt(payload: dict) -> str:
    padder = padding.PKCS7(128).padder()
    data = padder.update(json.dumps(payload).encode("utf-8")) + padder.finalize()
    encryptor = Cipher(
        algorithms.AES(bytes.fromhex(KEY_HEX)), modes.CBC(bytes.fromhex(IV_HEX))
    ).encryptor()
    return (encryptor.update(data) + encryptor.finalize()).hex()


def _decrypt(hex_text: str):
    decryptor = Cipher(
        algorithms.AES(bytes.fromhex(KEY_HEX)), modes.CBC(bytes.fromhex(IV_HEX))
    ).decryptor()
    padded = decryptor.update(bytes.fromhex(hex_text.strip())) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return json.loads(unpadder.update(padded) + unpadder.finalize())


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def _call(self, session: requests.Session, path: str, payload: dict):
        response = session.get(
            API_URL + path,
            headers={
                "P_PARAMETER": _encrypt(payload),
                "Accept": "application/json",
                "Content-type": "application/json; charset=UTF-8",
            },
            timeout=30,
        )
        response.raise_for_status()
        text = response.text.strip()
        if not re.fullmatch(r"[0-9A-Fa-f]+", text):
            raise ValueError(f"Unexpected response from iTouchVision {path}")
        return _decrypt(text)

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon") or kwargs.get("house_number")

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "Origin": "https://iapp.itouchvision.com",
                "Referer": "https://iapp.itouchvision.com/",
            }
        )

        client = self._call(
            session, "gdsv5/util/igetclientdetails", {"P_UID": HYNDBURN_UUID}
        )
        if client.get("P_IS_VALID") != 1:
            raise ValueError("iTouchVision rejected the Hyndburn client UUID")
        client_id = client["P_CLIENT_ID"]
        council_id = client["P_COUNCIL_ID"]

        if not user_uprn:
            if not user_postcode:
                raise ValueError("A UPRN or postcode must be provided")
            check_postcode(user_postcode)
            addresses = self._call(
                session,
                "kmbd/address",
                {
                    "P_POSTCODE": user_postcode.strip().upper(),
                    "P_LANG_CODE": "EN",
                    "P_CLIENT_ID": client_id,
                    "P_COUNCIL_ID": council_id,
                },
            ).get("ADDRESS", [])
            if not addresses:
                raise ValueError(f"No addresses found for postcode {user_postcode}")
            if user_paon:
                pattern = re.compile(rf"\b{re.escape(str(user_paon).strip())}\b", re.I)
                matches = [a for a in addresses if pattern.search(a["FULL_ADDRESS"])]
                if not matches:
                    raise ValueError(
                        f"Address '{user_paon}' not found for postcode {user_postcode}"
                    )
                user_uprn = matches[0]["UPRN"]
            elif len(addresses) == 1:
                user_uprn = addresses[0]["UPRN"]
            else:
                raise ValueError("Multiple addresses found; provide a UPRN or house number")

        check_uprn(str(user_uprn))

        result = self._call(
            session,
            "kmbd/collectionDay",
            {
                "P_UPRN": str(user_uprn),
                "P_CLIENT_ID": client_id,
                "P_COUNCIL_ID": council_id,
                "P_LANG_CODE": "EN",
            },
        )

        bins = []
        seen = set()
        for item in result.get("collectionDay", []) or []:
            bin_type = (item.get("binType") or "").strip()
            if not bin_type:
                continue
            for field in ("collectionDay", "followingDay"):
                raw = item.get(field)
                if not raw:
                    continue
                try:
                    date = datetime.strptime(raw, "%d-%m-%Y").strftime(date_format)
                except ValueError:
                    continue
                if (bin_type, date) in seen:
                    continue
                seen.add((bin_type, date))
                bins.append({"type": bin_type, "collectionDate": date})

        if not bins:
            raise ValueError("No collection data found")

        bins.sort(key=lambda x: datetime.strptime(x["collectionDate"], date_format))
        return {"bins": bins}
