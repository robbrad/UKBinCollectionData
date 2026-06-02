import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://fixmystreet.merton.gov.uk"


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
    MAX_POLLING_ATTEMPTS = 10
    POLLING_SLEEP_SECONDS = 3

    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        postcode = kwargs.get("postcode")
        paon = kwargs.get("paon")

        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
        )

        property_id = None

        if uprn and str(uprn).isdigit():
            r = s.get(f"{BASE_URL}/waste/{uprn}?page_loading=1",
                      headers={"x-requested-with": "fetch"}, timeout=10)
            if r.status_code == 200 and not r.url.endswith("/waste"):
                property_id = uprn

        if not property_id and postcode:
            property_id = _resolve_property_id(s, postcode, paon)

        if not property_id:
            raise ValueError("Could not resolve property. Provide postcode+address or valid Merton UPRN.")

        url = f"{BASE_URL}/waste/{property_id}?page_loading=1"
        headers = {"x-requested-with": "fetch"}

        data = {"bins": []}
        collections = []
        skip_services = ["Bulky waste", "Garden waste"]

        soup = None
        for attempt in range(self.MAX_POLLING_ATTEMPTS):
            response = s.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, features="html.parser")
            if soup.find_all("h3", class_="waste-service-name"):
                break
            time.sleep(self.POLLING_SLEEP_SECONDS)
        else:
            raise RuntimeError("Timeout waiting for bin collection data to load")

        grid_parent = soup.find("div", class_="govuk-grid-column-two-thirds")
        if not grid_parent:
            grid_parent = soup

        for grid in grid_parent.find_all("div", class_="waste-service-grid"):
            h3 = grid.find("h3", class_="waste-service-name")
            if not h3:
                continue
            bin_type = h3.get_text(strip=True)
            if bin_type in skip_services:
                continue

            for row in grid.find_all("div", class_="govuk-summary-list__row"):
                key = row.find("dt")
                value = row.find("dd")
                if not key or not value or "Next collection" not in key.get_text():
                    continue
                date_text = value.get_text(strip=True)
                parts = date_text.split()
                if len(parts) < 3:
                    continue
                day_str = parts[1]
                month_str = parts[2]
                year = datetime.now().year
                try:
                    dt = datetime.strptime(f"{day_str} {month_str} {year}", "%d %B %Y")
                    if dt.date() < datetime.now().date():
                        dt = dt.replace(year=year + 1)
                    collections.append((bin_type, dt))
                except ValueError:
                    continue

        ordered = sorted(collections, key=lambda x: x[1])
        for bin_type, dt in ordered:
            data["bins"].append({
                "type": bin_type.capitalize(),
                "collectionDate": dt.strftime(date_format),
            })

        return data
