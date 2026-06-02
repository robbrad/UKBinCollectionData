import re
import urllib.parse
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

QUERY_URL = "http://www.wyreforest.gov.uk/querybin.asp"

DAYS_OF_WEEK = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]


def _next_weekday(day_name: str, from_date: datetime = None) -> datetime:
    if from_date is None:
        from_date = datetime.now()
    target = next(i for i, d in enumerate(DAYS_OF_WEEK) if d.upper() == day_name.upper())
    current = from_date.weekday()
    days_ahead = (target - current) % 7
    if days_ahead == 0:
        return from_date
    return from_date + timedelta(days=days_ahead)


def _parse_result_page(soup) -> dict | None:
    text = soup.get_text(" ", strip=True)

    day_match = re.search(
        r"collected on a\s+(\w+)\s+on alternate weeks", text, re.I
    )
    if not day_match:
        return None

    collection_day = day_match.group(1).capitalize()
    if collection_day not in DAYS_OF_WEEK:
        return None

    green_vals = soup.find_all("font", color="#539253")
    vals = [v.get_text(strip=True) for v in green_vals]

    rubbish_next = None
    recycling_next = None
    if len(vals) >= 3:
        rubbish_next = vals[1]
        recycling_next = vals[2]

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    next_day = _next_weekday(collection_day, today)

    if rubbish_next and "today" in rubbish_next.lower():
        rubbish_start = today
        recycling_start = today + timedelta(days=7)
    elif rubbish_next and "next" in rubbish_next.lower():
        rubbish_start = next_day + timedelta(days=7) if next_day == today else next_day
        recycling_start = today if next_day == today else next_day - timedelta(days=7)
        if recycling_start < today:
            recycling_start = next_day
            rubbish_start = next_day + timedelta(days=7)
    elif recycling_next and "today" in recycling_next.lower():
        recycling_start = today
        rubbish_start = today + timedelta(days=7)
    elif recycling_next and "next" in recycling_next.lower():
        recycling_start = next_day + timedelta(days=7) if next_day == today else next_day
        rubbish_start = today if next_day == today else next_day - timedelta(days=7)
        if rubbish_start < today:
            rubbish_start = next_day
            recycling_start = next_day + timedelta(days=7)
    else:
        rubbish_start = next_day
        recycling_start = next_day + timedelta(days=7)

    return {
        "day": collection_day,
        "rubbish_start": rubbish_start,
        "recycling_start": recycling_start,
    }


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        street_name = (kwargs.get("paon") or "").strip()
        if not street_name:
            raise ValueError("Street name required in house_number/paon field")

        bindata = {"bins": []}

        params = {
            "txtStreetName": street_name.upper(),
            "locality": " ",
            "town": "",
            "select": "",
        }
        resp = requests.get(QUERY_URL, params=params, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        result = _parse_result_page(soup)
        if result is None:
            links = soup.find_all("a", href=re.compile(r"querybin\.asp.*select=yes", re.I))
            if not links:
                raise ValueError(f"No collection data found for street: {street_name}")

            for link in links:
                href = link.get("href", "")
                full_url = urllib.parse.urljoin(QUERY_URL, href)
                resp2 = requests.get(full_url, timeout=30)
                resp2.raise_for_status()
                soup2 = BeautifulSoup(resp2.text, "html.parser")
                result = _parse_result_page(soup2)
                if result is not None:
                    break

            if result is None:
                raise ValueError(f"Could not parse collection data for: {street_name}")

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(28):
            rubbish_date = result["rubbish_start"] + timedelta(weeks=i * 2)
            if rubbish_date >= today:
                bindata["bins"].append({
                    "type": "Black/Grey Rubbish Bin",
                    "collectionDate": rubbish_date.strftime("%d/%m/%Y"),
                })

            recycling_date = result["recycling_start"] + timedelta(weeks=i * 2)
            if recycling_date >= today:
                bindata["bins"].append({
                    "type": "Green Recycling Bin",
                    "collectionDate": recycling_date.strftime("%d/%m/%Y"),
                })

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
