import json

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

FORM_PAGE = "https://en.powys.gov.uk/binday"
FORM_ID = "BINDAYLOOKUP_FORM"
NEXT_TRIGGER = "BINDAYLOOKUP_ADDRESSLOOKUP_ADDRESSLOOKUPBUTTONS"

BIN_CARDS = [
    ("bdl-card--refuse", "General Rubbish / Wheelie bin"),
    ("bdl-card--recycling", "Recycling and Food Waste"),
    ("bdl-card--garden", "Garden Waste"),
]


def _form_fields(soup: BeautifulSoup) -> dict:
    form = soup.find("form", id=FORM_ID)
    return {
        inp.get("name"): inp.get("value") or ""
        for inp in form.find_all("input")
        if inp.get("name")
    }, form.get("action")


class CouncilClass(AbstractGetBinDataClass):
    """
    Powys County Council's bin-day finder is a GOSS iCM form, the same
    platform as Sunderland's - a plain HTTP postback wizard, plus a
    JSONP postcode-lookup endpoint the form calls client-side. No
    Selenium needed.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        check_paon(user_paon)
        check_postcode(user_postcode)
        data = {"bins": []}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        s = requests.Session()
        r = s.get(FORM_PAGE, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        fields, action = _form_fields(soup)

        jsonrpc = {
            "id": 1,
            "method": "postcodeSearch",
            "params": {"provider": "", "postcode": user_postcode},
        }
        r = s.get(
            "https://en.powys.gov.uk/apiserver/postcode",
            params={"jsonrpc": json.dumps(jsonrpc), "callback": "cb"},
            headers=headers,
            timeout=15,
        )
        r.raise_for_status()
        body = r.text
        if body.startswith("cb(") and body.endswith(")"):
            body = body[3:-1]
        addresses = json.loads(body).get("result") or []
        if len(addresses) == 1 and "Error" in addresses[0]:
            raise ValueError(addresses[0].get("Description", "Invalid postcode"))
        if not addresses:
            raise ValueError("No addresses found for this postcode")

        paon_upper = user_paon.strip().upper()
        match = next(
            (a for a in addresses if a["line1"].strip().upper() == paon_upper),
            None,
        ) or next(
            (a for a in addresses if a["line1"].strip().upper().startswith(paon_upper)),
            None,
        )
        if not match:
            raise ValueError(
                f"Could not match house name/number '{user_paon}' in address results"
            )

        fields["BINDAYLOOKUP_ADDRESSLOOKUP_ADDRESSLOOKUPPOSTCODE"] = user_postcode
        fields["BINDAYLOOKUP_ADDRESSLOOKUP_POSTALADDRESS"] = match["postalAddress"]
        fields["BINDAYLOOKUP_ADDRESSLOOKUP_UPRN"] = match["udprn"]
        fields["BINDAYLOOKUP_FORMACTION_NEXT"] = NEXT_TRIGGER

        post_headers = {**headers, "Referer": FORM_PAGE}
        r = s.post(action, data=fields, headers=post_headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for card_class, bin_type in BIN_CARDS:
            card = soup.find("div", class_=f"bdl-card {card_class}")
            if not card:
                continue
            for li in card.find_all("li"):
                date_text = li.get_text(strip=True).split(" (")[0]
                try:
                    collection_date = datetime.strptime(
                        remove_ordinal_indicator_from_date_string(date_text),
                        "%A %d %B %Y",
                    )
                except ValueError:
                    continue
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )

        data["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )
        return data
