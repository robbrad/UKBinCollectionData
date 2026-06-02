import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://waste-services.sutton.gov.uk"


def _resolve_property_id(s, postcode, paon):
    resp = s.post(f"{BASE_URL}/waste", data={"postcode": postcode}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    select = soup.find("select", {"id": "address"})
    if not select:
        return None

    paon_lower = (paon or "").strip().lower()
    best = None
    for opt in select.find_all("option"):
        val = opt.get("value", "")
        if not val or val == "missing":
            continue
        text = opt.get_text(strip=True).lower()
        if paon_lower and text.startswith(paon_lower):
            return val
        if not best and val:
            best = val

    return best


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        requests.packages.urllib3.disable_warnings()
        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": "uk-bin-collection/1.0 (+https://github.com/robbrad/UKBinCollectionData)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Connection": "close",
            }
        )
        retry = Retry(
            total=5,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=True,
        )
        s.mount("https://", HTTPAdapter(max_retries=retry))

        user_uprn = kwargs.get("uprn")
        postcode = kwargs.get("postcode")
        paon = kwargs.get("paon")

        property_id = None

        if user_uprn:
            r = s.get(f"{BASE_URL}/waste/{user_uprn}", timeout=30)
            if r.status_code == 200 and "Loading your bin days" not in r.text[:2000]:
                property_id = user_uprn
            elif r.status_code == 200:
                for _ in range(5):
                    time.sleep(2)
                    r = s.get(f"{BASE_URL}/waste/{user_uprn}", timeout=30)
                    if "Loading your bin days" not in r.text[:2000]:
                        property_id = user_uprn
                        break

        if not property_id and postcode:
            property_id = _resolve_property_id(s, postcode, paon)

        if not property_id:
            raise ValueError("Could not resolve property. Provide postcode+address or valid Sutton UPRN.")

        max_retries = 10
        soup = None
        for attempt in range(max_retries):
            r = s.get(f"{BASE_URL}/waste/{property_id}", timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            if soup.find_all("h3", class_="waste-service-name"):
                break
            time.sleep(3)
        else:
            raise RuntimeError("Sutton page returned no service data after retries")
        data = {"bins": []}

        for service in soup.find_all("h3", class_="waste-service-name"):
            service_title = service.get_text(strip=True)
            parent = service.find_parent("div", class_="waste-service-grid")
            if not parent:
                continue
            for row in parent.find_all("div", class_="govuk-summary-list__row"):
                next_coll = row.find("dt", string="Next collection")
                if not next_coll:
                    continue
                date_text = next_coll.find_next_sibling().get_text(strip=True)
                date_part = date_text.split(",")[1].strip() if "," in date_text else date_text.strip()
                parts = date_part.split()[:2]
                if len(parts) < 2:
                    continue
                day_str = remove_ordinal_indicator_from_date_string(parts[0])
                month_str = parts[1]
                try:
                    dt = datetime.strptime(f"{day_str} {month_str}", "%d %B")
                    year = datetime.now().year
                    dt = dt.replace(year=year)
                    if dt < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                        dt = dt.replace(year=year + 1)
                    data["bins"].append({
                        "type": service_title,
                        "collectionDate": dt.strftime(date_format),
                    })
                except ValueError:
                    continue

        data["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )
        return data
