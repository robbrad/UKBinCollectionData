import hashlib
import os
import re
import time
from datetime import datetime

import pdfplumber
import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

ISHARE_BASE = "http://maps.easthants.gov.uk"
PDF_CACHE_DIR = "/home/mark/pdf-scrapers/easthants"
PDF_CACHE_MAX_AGE = 86400 * 7


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)

        props = self._get_property(user_postcode, user_paon)
        if not props:
            raise ValueError(f"No property found for {user_postcode}")

        uid = props["UniqueId"]
        x = props["X"]
        y = props["Y"]

        calendar_num, garden_num = self._get_calendar_info(uid, x, y)

        if not calendar_num:
            raise ValueError("No bin calendar found for property")

        pdf_url = self._build_pdf_url(calendar_num)
        if pdf_url:
            pdf_path = self._get_pdf(pdf_url)
            dates = self._parse_pdf(pdf_path)

            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            for dt in dates:
                if dt >= today:
                    data["bins"].append({
                        "type": "Waste Collection",
                        "collectionDate": dt.strftime(date_format),
                    })

        if garden_num:
            gpdf_url = self._build_garden_pdf_url(garden_num)
            if gpdf_url:
                try:
                    gpdf_path = self._get_pdf(gpdf_url)
                    gdates = self._parse_pdf(gpdf_path)
                    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    for dt in gdates:
                        if dt >= today:
                            data["bins"].append({
                                "type": "Garden Waste",
                                "collectionDate": dt.strftime(date_format),
                            })
                except Exception:
                    pass

        if data["bins"]:
            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
            )

        return data

    def _get_property(self, postcode, paon):
        params = {
            "type": "json", "service": "LocationSearch",
            "RequestType": "LocationSearch",
            "location": postcode, "pagesize": "30",
            "startnum": "1", "gettotals": "false",
            "mapsource": "EHDC/MyHouse",
        }
        resp = requests.get(
            f"{ISHARE_BASE}/GetData.aspx", params=params,
            headers=HEADERS, timeout=30
        )
        resp.raise_for_status()
        result = resp.json()
        columns = result.get("columns", [])
        rows = result.get("data", [])

        if not rows:
            return None

        records = [dict(zip(columns, row)) for row in rows]

        if paon:
            for rec in records:
                name = re.sub(r"<[^>]+>", "", rec.get("DisplayName", ""))
                if name.lower().startswith(paon.lower()):
                    return rec
            for rec in records:
                name = re.sub(r"<[^>]+>", "", rec.get("DisplayName", ""))
                if paon.lower() in name.lower():
                    return rec

        return records[0]

    def _get_calendar_info(self, uid, x, y):
        params = {
            "UniqueId": uid, "type": "Property_EHDC",
            "x": x, "y": y, "ms": "EHDC/MyHouse",
        }
        resp = requests.get(
            f"{ISHARE_BASE}/easthampshire.aspx", params=params,
            headers=HEADERS, timeout=30
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()

        cal_match = re.search(r"Calendar:?\s*\[?(\d+|H\d+)\]?", text, re.I)
        garden_match = re.search(r"Garden\s*(?:Waste)?\s*Calendar:?\s*\[?(G\d+)\]?", text, re.I)

        calendar_num = cal_match.group(1) if cal_match else None
        garden_num = garden_match.group(1) if garden_match else None

        return calendar_num, garden_num

    def _build_pdf_url(self, calendar_num):
        num_str = calendar_num.zfill(2) if calendar_num.isdigit() else calendar_num
        return f"https://www.easthants.gov.uk/sites/default/files/2025-09/norse_{num_str}_0925.pdf"

    def _build_garden_pdf_url(self, garden_num):
        return f"https://www.easthants.gov.uk/sites/default/files/2025-09/{garden_num}_0925.pdf"

    def _get_pdf(self, pdf_url):
        os.makedirs(PDF_CACHE_DIR, exist_ok=True)
        url_hash = hashlib.md5(pdf_url.encode()).hexdigest()[:12]
        pdf_path = os.path.join(PDF_CACHE_DIR, f"cal_{url_hash}.pdf")

        if os.path.exists(pdf_path):
            age = time.time() - os.path.getmtime(pdf_path)
            if age < PDF_CACHE_MAX_AGE:
                return pdf_path

        resp = requests.get(pdf_url, headers=HEADERS, timeout=60, allow_redirects=True)
        resp.raise_for_status()

        if not resp.content[:4] == b"%PDF":
            raise ValueError(f"URL did not return a PDF: {pdf_url}")

        with open(pdf_path, "wb") as f:
            f.write(resp.content)

        return pdf_path

    def _parse_pdf(self, pdf_path):
        dates = []
        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text()

        if not text:
            return dates

        current_months = []

        for line in text.split("\n"):
            month_matches = re.findall(
                r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(20\d{2})",
                line,
            )
            if month_matches:
                current_months = [
                    (MONTHS[m], int(y)) for m, y in month_matches
                ]
                continue

            day_matches = re.findall(
                r"(?:MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{1,2})", line
            )
            if day_matches and current_months:
                for i, day_str in enumerate(day_matches):
                    if i < len(current_months):
                        month, year = current_months[i]
                        try:
                            dt = datetime(year, month, int(day_str))
                            dates.append(dt)
                        except ValueError:
                            continue

        return sorted(set(dates))
