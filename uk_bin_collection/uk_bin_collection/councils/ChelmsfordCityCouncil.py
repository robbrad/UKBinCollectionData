import io
import re
from datetime import datetime, timedelta

import pdfplumber
import requests
from bs4 import BeautifulSoup
from icalevents.icalevents import events

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# Marker fills on the council's PDF calendar. A dark circle is a black bin week,
# a green square is a brown bin week; the day number is printed inside it.
BLACK_BIN_COLOR = (0.28, 0.28, 0.28)
BROWN_BIN_COLOR = (0.27, 0.54, 0.15)
MONTH_HEADER_COLOR = (0.96, 0.85, 0.91)
COLOR_TOLERANCE = 0.05

BLACK_BIN_WEEK = ["Food Waste", "Black Bin", "Green Box", "Card Sack"]
BROWN_BIN_WEEK = ["Food Waste", "Brown Bin", "Plastics & Cartons", "Paper Sack"]

MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]


def _color_matches(color, target):
    if not isinstance(color, (list, tuple)) or len(color) != len(target):
        return False
    return all(abs(a - b) <= COLOR_TOLERANCE for a, b in zip(color, target))


def _parse_calendar_pdf(pdf_bytes):
    """Return [(date, [bin types])] from a Chelmsford kerbside calendar PDF.

    Month grids are found from their pink header bars ("November 2026"). Each
    black/green marker is matched to the grid it sits under and to the day
    number printed inside it, so collections moved to another weekday for a
    bank holiday are picked up without special handling.
    """
    page = pdfplumber.open(io.BytesIO(pdf_bytes)).pages[0]
    words = page.extract_words()

    headers = []
    for rect in page.rects:
        if not _color_matches(rect.get("non_stroking_color"), MONTH_HEADER_COLOR):
            continue
        inside = [
            w["text"]
            for w in words
            if rect["x0"] - 1 <= w["x0"] and w["x1"] <= rect["x1"] + 1
            and rect["top"] - 1 <= w["top"] and w["bottom"] <= rect["bottom"] + 1
        ]
        month = next((MONTHS.index(t.lower()) + 1 for t in inside if t.lower() in MONTHS), None)
        year = next((int(t) for t in inside if re.fullmatch(r"20\d{2}", t)), None)
        if month and year:
            headers.append({**{k: rect[k] for k in ("x0", "x1", "bottom")}, "month": month, "year": year})
    if not headers:
        raise ValueError("No month grids found in PDF calendar")

    markers = [
        (r, BROWN_BIN_WEEK)
        for r in page.rects
        if _color_matches(r.get("non_stroking_color"), BROWN_BIN_COLOR)
        and 10 < r["width"] < 20
    ] + [
        (c, BLACK_BIN_WEEK)
        for c in page.curves
        if _color_matches(c.get("non_stroking_color"), BLACK_BIN_COLOR)
        and 10 < c["width"] < 20
    ]

    results = []
    for shape, bins in markers:
        cx = (shape["x0"] + shape["x1"]) / 2
        cy = (shape["top"] + shape["bottom"]) / 2
        grids = [
            h for h in headers if h["x0"] <= cx <= h["x1"] and h["bottom"] <= cy
        ]
        if not grids:
            continue
        grid = max(grids, key=lambda h: h["bottom"])
        number = next(
            (
                w["text"]
                for w in words
                if w["text"].isdigit()
                and shape["x0"] <= (w["x0"] + w["x1"]) / 2 <= shape["x1"]
                and shape["top"] <= (w["top"] + w["bottom"]) / 2 <= shape["bottom"]
            ),
            None,
        )
        if number is None:
            continue
        try:
            results.append((datetime(grid["year"], grid["month"], int(number)), bins))
        except ValueError:
            continue

    if not results:
        raise ValueError("No collection markers found in PDF calendar")
    return sorted(results, key=lambda r: r[0])


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        """
        Locate the council collection round for the given address and return upcoming bin
        collection dates and types within the next 60 days.

        Uses HTTP requests only — the search form submits via GET querystring
        (`?<block_id>_keyword=<postcode>`) and renders a results table directly in static
        HTML. Avoids Selenium entirely so we don't have to dismiss the emarsys popup +
        Civic cookie banner that intercept clicks on the live page.

        Parameters:
            page (str): Unused, kept for API compatibility.
            postcode (str, in kwargs): Postcode to search.
            paon (str, in kwargs): Property/house name or number used to match the row.

        Returns:
            dict: {"bins": [{"type": ..., "collectionDate": ...}, ...]}

        Raises:
            ValueError: If no collection round is found for `paon`, or the .ics calendar
                link for the identified round can't be located.
        """
        try:
            data = {"bins": []}
            postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            session = requests.Session()
            base_url = "https://www.chelmsford.gov.uk/bins-and-recycling/check-your-collection-day/"

            # Step 1: load the search page to discover the dynamic block ID used
            # in the form input (e.g. `14532_keyword`). The ID has been stable but
            # extracting it keeps the scraper resilient if the council republishes
            # the block.
            r = session.get(base_url, headers=headers, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            input_el = soup.find("input", id=re.compile(r"\d+_keyword"))
            if not input_el:
                raise ValueError(
                    "Could not locate postcode input on the council search page"
                )
            form_id = input_el["id"].split("_")[0]

            # Step 2: submit the search via querystring (mirrors what the form's
            # JS submit handler does on the live page).
            search_url = (
                f"{base_url}?{form_id}_keyword={requests.utils.quote(postcode)}"
                f"#search-{form_id}"
            )
            r = session.get(search_url, headers=headers, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            # Step 3: walk the results table to find the row matching `paon`.
            # The row format is `<tr><td>full address</td><td><p>This property is
            # covered by the Tuesday B collection round...</p></td></tr>`.
            table = soup.find("table", class_="directories-table__table")
            if table is None:
                # Fallback: any table on the page
                table = soup.find("table")

            calendar_url = None
            if table is not None:
                for row in table.find_all("tr"):
                    if user_paon in row.get_text():
                        row_text = row.get_text()
                        round_match = re.search(
                            r"(Monday|Tuesday|Wednesday|Thursday|Friday)\s+([AB])",
                            row_text,
                        )
                        if round_match:
                            day = round_match.group(1).lower()
                            letter = round_match.group(2).lower()
                            calendar_url = (
                                f"https://www.chelmsford.gov.uk/bins-and-recycling/"
                                f"check-your-collection-day/{day}-{letter}-collection-calendar/"
                            )
                            break

            if calendar_url is None:
                # Fallback: the search page also exposes per-property cards as
                # <details> blocks containing a paragraph with the round name and
                # a calendar link. Use the first card whose summary contains the
                # paon.
                for details in soup.find_all("details"):
                    if user_paon in details.get_text():
                        a = details.find(
                            "a",
                            href=lambda h: h and "collection-calendar" in h,
                        )
                        if a:
                            calendar_url = a["href"]
                            break

            if calendar_url is None:
                raise ValueError(
                    f"Could not find collection round for address: {user_paon}"
                )

            # Step 4: fetch the round's calendar page. The council used to publish
            # an .ics file here and now publishes a PDF, so take whichever exists.
            r = session.get(calendar_url, headers=headers, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            now = datetime.now()
            future = now + timedelta(days=60)

            ics_link = soup.find("a", href=lambda h: h and h.lower().endswith(".ics"))
            if ics_link:
                # Step 5a: parse the ICS calendar for events in the next 60 days.
                upcoming_events = events(ics_link["href"], start=now, end=future)
                for event in sorted(upcoming_events, key=lambda e: e.start):
                    if event.summary and event.start:
                        for collection in event.summary.split(","):
                            data["bins"].append(
                                {
                                    "type": collection.strip(),
                                    "collectionDate": event.start.date().strftime(
                                        date_format
                                    ),
                                }
                            )
                return data

            pdf_link = soup.find(
                "a",
                href=lambda h: h
                and h.lower().split("?")[0].endswith(".pdf")
                and "calendar" in h.lower(),
            )
            if not pdf_link:
                raise ValueError(
                    f"Could not find collection calendar (ICS or PDF) for address: {user_paon}"
                )
            pdf_url = requests.compat.urljoin(calendar_url, pdf_link["href"])

            # Step 5b: read the PDF calendar for collections in the next 60 days.
            r = session.get(pdf_url, headers=headers, timeout=30)
            r.raise_for_status()
            if r.content[:4] != b"%PDF":
                raise ValueError(f"Could not download PDF calendar from {pdf_url}")

            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            for collection_date, bin_types in _parse_calendar_pdf(r.content):
                if today <= collection_date <= future:
                    for bin_type in bin_types:
                        data["bins"].append(
                            {
                                "type": bin_type,
                                "collectionDate": collection_date.strftime(
                                    date_format
                                ),
                            }
                        )
        except Exception as e:
            print(f"An error occurred: {e}")
            raise

        return data
