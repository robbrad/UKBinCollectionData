import hashlib
import json
import os
import re
import tempfile
import time
from datetime import datetime

import pdfplumber
import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

ISHARE_BASE = "https://maps.easthants.gov.uk"
PDF_CACHE_DIR = os.path.join(tempfile.gettempdir(), "ukbcd-easthants-pdf")
PDF_CACHE_MAX_AGE = 86400 * 7
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

MONTHS = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
]

# Each collection day in the calendar sits on a coloured cell, and the colour
# is the only thing saying which bin goes out - the text just gives the day.
# The legend reads "Rubbish (black bin)" and "Recycling (green bin) and glass
# box(es)"; orange marks a collection moved for a bank holiday, and the PDF
# doesn't say which bin that one is.
CELL_COLOURS = [
    ((0.248, 0.646, 0.209), "Recycling (green bin) and glass box(es)"),
    ((0.391, 0.389, 0.387), "Rubbish (black bin)"),
    ((0.971, 0.66, 0.0), "Collection (bank holiday change)"),
]
COLOUR_TOLERANCE = 0.08

# A day number belongs to the month header nearest it horizontally. Columns are
# ~82pt apart in the calendars seen so far, so half that is a safe radius.
COLUMN_RADIUS = 45


def _colour_matches(colour, reference, tol=COLOUR_TOLERANCE):
    if not colour or len(colour) != len(reference):
        return False
    return all(abs(a - b) <= tol for a, b in zip(colour, reference))


def _bin_type_for(colour):
    for reference, name in CELL_COLOURS:
        if _colour_matches(colour, reference):
            return name
    return None


def _find_month_headers(words):
    """
    Locate each "<MON> <YYYY>" heading, with the position it sits at.

    The calendar is laid out as four month columns side by side, so a single
    text line holds days for four different months. Anything that reads the
    text line by line - as this scraper used to - files every one of those
    days under whichever month it matched first.
    """
    headers = []
    for word in words:
        if word["text"].upper() not in MONTHS:
            continue
        for other in words:
            if (
                other["text"].isdigit()
                and len(other["text"]) == 4
                and abs(other["top"] - word["top"]) < 3
                and 0 < other["x0"] - word["x1"] < 20
            ):
                headers.append(
                    {
                        "month": MONTHS.index(word["text"].upper()) + 1,
                        "year": int(other["text"]),
                        "x0": word["x0"],
                        "top": word["top"],
                    }
                )
                break
    return headers


def _smallest_cell_colour(word, rects):
    """The fill colour of the tightest rectangle enclosing this day number."""
    cx = (word["x0"] + word["x1"]) / 2
    cy = (word["top"] + word["bottom"]) / 2
    enclosing = [
        r for r in rects if r["x0"] <= cx <= r["x1"] and r["top"] <= cy <= r["bottom"]
    ]
    if not enclosing:
        return None
    enclosing.sort(key=lambda r: (r["x1"] - r["x0"]) * (r["bottom"] - r["top"]))
    return enclosing[0].get("non_stroking_color")


def extract_collections(words, rects):
    """
    Turn a calendar page's words and rectangles into (bin type, date) pairs.

    Split out from the PDF handling so the column and colour logic can be
    tested offline against synthetic pages.
    """
    headers = _find_month_headers(words)
    collections = []

    for word in words:
        text = word["text"]
        if not (text.isdigit() and len(text) <= 2):
            continue
        day = int(text)
        if not 1 <= day <= 31:
            continue

        # The day belongs to the nearest header in its own column that sits
        # above it on the page.
        candidates = [
            h
            for h in headers
            if abs(h["x0"] - word["x0"]) < COLUMN_RADIUS and h["top"] < word["top"]
        ]
        if not candidates:
            continue
        header = max(candidates, key=lambda h: h["top"])

        bin_type = _bin_type_for(_smallest_cell_colour(word, rects))
        if bin_type is None:
            # Not a collection cell - page furniture that happens to be a number.
            continue

        try:
            date = datetime(header["year"], header["month"], day)
        except ValueError:
            continue
        collections.append((bin_type, date))

    collections.sort(key=lambda pair: pair[1])
    return collections


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

        collections = self._parse_pdf(pdf_url)
        if not collections:
            raise ValueError(
                f"No collection dates could be read from East Hampshire's "
                f"calendar {cal_num} ({pdf_url})."
            )

        now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for bin_type, date in collections:
            if date >= now:
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": date.strftime(date_format),
                    }
                )

        if not data["bins"]:
            latest = collections[-1][1].strftime(date_format)
            raise ValueError(
                f"East Hampshire's calendar {cal_num} only runs to {latest}, so it "
                f"has no collections left. The council should have published a new "
                f"one - if this persists, the calendar link may need revisiting."
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
            PDF_CACHE_DIR,
            hashlib.md5(pdf_url.encode(), usedforsecurity=False).hexdigest() + ".pdf",
        )

        if (
            not os.path.exists(cache_path)
            or (time.time() - os.path.getmtime(cache_path)) > PDF_CACHE_MAX_AGE
        ):
            r = requests.get(pdf_url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            if not r.content.startswith(b"%PDF"):
                raise ValueError(
                    f"East Hampshire's calendar URL did not return a PDF: {pdf_url}"
                )
            tmp_path = cache_path + ".tmp"
            with open(tmp_path, "wb") as f:
                f.write(r.content)
            os.replace(tmp_path, cache_path)

        collections = []
        with pdfplumber.open(cache_path) as pdf:
            for page in pdf.pages:
                collections.extend(
                    extract_collections(page.extract_words(), page.rects)
                )

        collections.sort(key=lambda pair: pair[1])
        return collections
