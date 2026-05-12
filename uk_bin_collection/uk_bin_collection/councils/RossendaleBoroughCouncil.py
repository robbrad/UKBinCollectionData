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
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4,
    "MAY": 5, "JUNE": 6, "JULY": 7, "AUGUST": 8,
    "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
}

PDF_CACHE_DIR = "/home/mark/pdf-scrapers/rossendale"
PDF_CACHE_MAX_AGE = 86400 * 7


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)

        base_url = "https://www.rossendale.gov.uk"

        search_url = (
            f"{base_url}/directory/search"
            f"?directoryID=10094&keywords={user_postcode.replace(' ', '+')}"
        )
        resp = requests.get(search_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        records = soup.find_all("a", href=re.compile(r"/directory-record/\d+/"))

        if not records:
            raise ValueError(f"No addresses found for {user_postcode}")

        record_url = None
        if user_paon:
            for rec in records:
                text = rec.get_text(strip=True)
                if text.lower().startswith(user_paon.lower()):
                    record_url = base_url + rec["href"]
                    break
            if not record_url:
                for rec in records:
                    text = rec.get_text(strip=True)
                    if user_paon.lower() in text.lower():
                        record_url = base_url + rec["href"]
                        break

        if not record_url:
            record_url = base_url + records[0]["href"]

        resp = requests.get(record_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        dl_links = soup.find_all("a", href=re.compile(r"/downloads/file/\d+/"))

        if not dl_links:
            raise ValueError("No calendar PDF link found on property page")

        pdf_url = dl_links[0]["href"]
        if not pdf_url.startswith("http"):
            pdf_url = base_url + pdf_url

        pdf_path = self._get_pdf(pdf_url)
        bins = self._parse_pdf(pdf_path)

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for dt, bin_type in bins:
            if dt >= today:
                data["bins"].append({
                    "type": bin_type,
                    "collectionDate": dt.strftime(date_format),
                })

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data

    def _get_pdf(self, pdf_url):
        os.makedirs(PDF_CACHE_DIR, exist_ok=True)
        url_hash = hashlib.md5(pdf_url.encode()).hexdigest()[:12]
        pdf_path = os.path.join(PDF_CACHE_DIR, f"zone_{url_hash}.pdf")

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
        bins = []

        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text()

        if not text:
            return bins

        lines = text.strip().split("\n")

        general_dates = []
        recycling_dates = []

        for line in lines:
            m = re.match(
                r"^(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|"
                r"SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(\d{2})\s+"
                r"([\d\s]+?)\s+"
                r"(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|"
                r"SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(\d{2})\s+"
                r"([\d\s]+)$",
                line.strip(),
            )
            if not m:
                continue

            gen_month = MONTHS[m.group(1)]
            gen_year = 2000 + int(m.group(2))
            gen_days = [int(d) for d in m.group(3).split()]

            rec_month = MONTHS[m.group(4)]
            rec_year = 2000 + int(m.group(5))
            rec_days = [int(d) for d in m.group(6).split()]

            for day in gen_days:
                try:
                    dt = datetime(gen_year, gen_month, day)
                    general_dates.append(dt)
                except ValueError:
                    continue

            for day in rec_days:
                try:
                    dt = datetime(rec_year, rec_month, day)
                    recycling_dates.append(dt)
                except ValueError:
                    continue

        for dt in general_dates:
            bins.append((dt, "General Waste"))
            bins.append((dt, "Food Waste"))

        for dt in recycling_dates:
            bins.append((dt, "Recycling"))

        bins.sort(key=lambda x: x[0])
        return bins
