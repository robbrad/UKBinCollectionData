import os
import re
import json
import time
import hashlib
from datetime import datetime

import pdfplumber
import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

ISHARE_BASE = "https://maps.easthants.gov.uk"
PDF_CACHE_DIR = "/home/mark/pdf-scrapers/easthants"
PDF_CACHE_MAX_AGE = 86400 * 7
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)

        uid = self._get_property_uid(user_postcode, user_paon)
        cal_num, pdf_url = self._get_calendar(uid)

        if not pdf_url:
            raise ValueError(f"No calendar found for property {uid}")

        dates = self._parse_pdf(pdf_url)
        now = datetime.now()
        for bin_type, dt in dates:
            if dt >= now:
                data["bins"].append({
                    "type": bin_type,
                    "collectionDate": dt.strftime(date_format),
                })

        data["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )
        return data

    def _get_property_uid(self, postcode, paon):
        r = requests.get(
            f"{ISHARE_BASE}/getdata.aspx",
            params={
                "service": "Location",
                "RequestType": "LocationSearch",
                "location": postcode,
                "pagesize": "50",
                "startnum": "1",
                "mapsource": "EHDC/MyHouse",
            },
            headers=HEADERS,
            timeout=30,
        )
        r.raise_for_status()
        result = r.json()
        rows = result.get("data", [])

        if not rows:
            raise ValueError(f"No properties found for {postcode}")

        if paon:
            paon_upper = paon.upper()
            for row in rows:
                name = row[7].upper() if len(row) > 7 else ""
                if name.startswith(paon_upper) or paon_upper in name:
                    return row[0]

        return rows[0][0]

    def _get_calendar(self, uid):
        r = requests.get(
            f"{ISHARE_BASE}/getdata.aspx",
            params={
                "RequestType": "LocalInfo",
                "ms": "EHDC/MyHouse",
                "format": "JSONP",
                "uid": uid,
                "group": "Waste and Recycling|Bin Calendar",
            },
            headers=HEADERS,
            timeout=30,
        )
        r.raise_for_status()
        match = re.match(r"[^(]+\((.+)\);\s*$", r.text, re.S)
        if not match:
            return None, None

        data = json.loads(match.group(1))
        cal_str = data.get("Results", {}).get("Bin_Calendar", {}).get("_Calendar", "")
        if "|" in cal_str:
            pdf_url, cal_num = cal_str.rsplit("|", 1)
            return cal_num, pdf_url
        return None, None

    def _parse_pdf(self, pdf_url):
        os.makedirs(PDF_CACHE_DIR, exist_ok=True)
        cache_path = os.path.join(
            PDF_CACHE_DIR, hashlib.md5(pdf_url.encode()).hexdigest() + ".pdf"
        )

        if not os.path.exists(cache_path) or (time.time() - os.path.getmtime(cache_path)) > PDF_CACHE_MAX_AGE:
            r = requests.get(pdf_url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            with open(cache_path, "wb") as f:
                f.write(r.content)

        dates = []
        current_year = datetime.now().year

        with pdfplumber.open(cache_path) as pdf:
            for pg in pdf.pages:
                text = pg.extract_text() or ""
                lines = text.split("\n")
                current_month = None
                for line in lines:
                    line_upper = line.strip().upper()
                    for month_name, month_num in MONTHS.items():
                        if line_upper.startswith(month_name) or f" {month_name}" in line_upper:
                            current_month = month_num
                            break
                    if current_month:
                        day_matches = re.findall(r"\b(\d{1,2})\b", line)
                        for day_str in day_matches:
                            day = int(day_str)
                            if 1 <= day <= 31:
                                try:
                                    dt = datetime(current_year, current_month, day)
                                    dates.append(("Waste Collection", dt))
                                except ValueError:
                                    pass
        return dates
