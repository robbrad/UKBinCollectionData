import json
import re

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def _normalise(text) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", str(text).upper()).strip()


def _extract_json_array(text: str, marker: str, start_from: int = 0):
    """Pull the JSON array passed to ejs.data.DataUtil.parse.isJson(...) after marker."""
    idx = text.index(marker, start_from) + len(marker)
    start = text.index("[", idx)
    array, _ = json.JSONDecoder().raw_decode(text, start)
    return array


class CouncilClass(AbstractGetBinDataClass):
    """
    Slough Borough Council uses a Syncfusion-based "Public Dashboard"
    (waste.slough.gov.uk) that renders premises and the collection schedule
    as plain server-rendered JSON embedded in the page - no browser needed.
    Other councils on the same platform subclass this with their own BASE_URL.
    """

    BASE_URL = "https://waste.slough.gov.uk/PublicDashboard"

    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        user_uprn = kwargs.get("uprn")
        check_postcode(user_postcode)
        bindata = {"bins": []}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        s = requests.Session()
        r = s.get(self.BASE_URL, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        token = soup.find("input", {"name": "__RequestVerificationToken"})["value"]

        post_headers = {
            **headers,
            "Referer": self.BASE_URL,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        r = s.post(
            f"{self.BASE_URL}?handler=SearchPostcode",
            data={
                "SelectedPostcode": user_postcode,
                "__RequestVerificationToken": token,
            },
            headers=post_headers,
            timeout=15,
        )
        r.raise_for_status()
        premises = _extract_json_array(r.text, "ejs.data.DataUtil.parse.isJson(")
        if not premises:
            raise ValueError("No addresses found for this postcode")

        soup = BeautifulSoup(r.text, "html.parser")
        token = soup.find("input", {"name": "__RequestVerificationToken"})["value"]

        if user_uprn:
            check_uprn(user_uprn)
            match = next(
                (p for p in premises if str(int(p["UPRN"])) == str(user_uprn)), None
            )
            if not match:
                raise ValueError(
                    f"Could not match UPRN '{user_uprn}' in address results"
                )
        elif user_paon:
            check_paon(user_paon)
            # Ignore punctuation so "9 Ellison Street, Glossop" matches
            # however the dashboard formats the premises text.
            paon_norm = _normalise(user_paon)
            match = next(
                (
                    p
                    for p in premises
                    if (_normalise(p["Premises"]) + " ").startswith(paon_norm + " ")
                ),
                None,
            )
            if not match:
                raise ValueError(
                    f"Could not match house number '{user_paon}' in address results"
                )
        elif len(premises) == 1:
            match = premises[0]
        else:
            raise ValueError(
                "Multiple addresses found for this postcode; provide a UPRN or house number to disambiguate"
            )

        r = s.post(
            f"{self.BASE_URL}?handler=SelectPrem",
            data={
                "SelectedPostcode": user_postcode,
                "SelectedPremises": str(int(match["UPRN"])),
                "__RequestVerificationToken": token,
            },
            headers=post_headers,
            timeout=15,
        )
        r.raise_for_status()
        events = _extract_json_array(
            r.text, "ejs.data.DataUtil.parse.isJson(", r.text.index("eventSettings")
        )

        today = datetime.now().date()
        for event in events:
            collection_date = datetime.fromisoformat(event["StartTime"]).date()
            if collection_date < today:
                continue
            bindata["bins"].append(
                {
                    "type": event["Subject"].title(),
                    "collectionDate": collection_date.strftime(date_format),
                }
            )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
