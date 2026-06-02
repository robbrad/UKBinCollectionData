import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

API_BASE = "https://api.blackpool.gov.uk/live//api/bartec"

HEADERS = {
    "Accept": "*/*",
    "Origin": "https://www.blackpool.gov.uk",
    "Referer": "https://www.blackpool.gov.uk/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
}


def _get_token():
    r = requests.get(f"{API_BASE}/security/token", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text.strip().replace('"', "")


def _make_payload(uprn, postcode, token):
    return {
        "UPRN": uprn or "",
        "USRN": "",
        "PostCode": postcode or "",
        "StreetNumber": "",
        "CurrentUser": {"UserId": "", "Token": token},
    }


def _find_uprn_by_address(postcode, paon, token):
    payload = _make_payload("", postcode, token)
    r = requests.post(f"{API_BASE}/collection/Premises", headers=HEADERS, json=payload, timeout=30)
    r.raise_for_status()
    premises = r.json().get("premisesField") or []

    paon_lower = (paon or "").strip().lower()
    for p in premises:
        addr = p.get("addressField", {})
        house_num = (addr.get("address2Field") or "").strip().lower()
        if paon_lower and house_num == paon_lower:
            uprn_val = p.get("uPRNField")
            if uprn_val:
                return str(int(uprn_val))

    return None


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)
        bindata = {"bins": []}

        token = _get_token()

        result = None
        if user_uprn:
            payload = _make_payload(user_uprn, user_postcode, token)
            r = requests.post(f"{API_BASE}/collection/PremiseJobs", headers=HEADERS, json=payload, timeout=30)
            r.raise_for_status()
            result = r.json()

        if not result or not result.get("jobsField"):
            resolved = _find_uprn_by_address(user_postcode, user_paon, token)
            if resolved and resolved != str(user_uprn):
                payload = _make_payload(resolved, user_postcode, token)
                r = requests.post(f"{API_BASE}/collection/PremiseJobs", headers=HEADERS, json=payload, timeout=30)
                r.raise_for_status()
                result = r.json()

        if not result or not result.get("jobsField"):
            return bindata

        for collection in result["jobsField"]:
            job = collection.get("jobField", {})
            date = job.get("scheduledStartField")
            bin_type = job.get("nameField", "") or job.get("descriptionField", "")
            if not date or not bin_type:
                continue

            bindata["bins"].append({
                "type": bin_type,
                "collectionDate": datetime.strptime(date, "%Y-%m-%dT%H:%M:%S").strftime(date_format),
            })

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
