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
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
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
            if rect["x0"] - 1 <= w["x0"]
            and w["x1"] <= rect["x1"] + 1
            and rect["top"] - 1 <= w["top"]
            and w["bottom"] <= rect["bottom"] + 1
        ]
        month = next(
            (MONTHS.index(t.lower()) + 1 for t in inside if t.lower() in MONTHS), None
        )
        year = next((int(t) for t in inside if re.fullmatch(r"20\d{2}", t)), None)
        if month and year:
            headers.append(
                {
                    **{k: rect[k] for k in ("x0", "x1", "bottom")},
                    "month": month,
                    "year": year,
                }
            )
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
        grids = [h for h in headers if h["x0"] <= cx <= h["x1"] and h["bottom"] <= cy]
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


def _clean(text):
    return re.sub(r"\s+", " ", text).strip()


def _extract_candidates(soup):
    """Return [{"address", "calendar_url"}] for each property in the search results.

    Results normally come as table rows (`<td>address</td><td>covered by the
    Tuesday B collection round</td>`); if there is no table, fall back to
    <details> cards whose summary is the address and which link to the calendar.
    `calendar_url` is None when the council can't show a round for the property.
    """
    base = "https://www.chelmsford.gov.uk/bins-and-recycling/check-your-collection-day/"
    candidates = []
    table = soup.find("table", class_="directories-table__table") or soup.find("table")
    if table is not None:
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            round_match = re.search(
                r"(Monday|Tuesday|Wednesday|Thursday|Friday)\s+([AB])\b",
                " ".join(c.get_text(" ") for c in cells[1:]),
            )
            calendar_url = (
                f"{base}{round_match.group(1).lower()}-{round_match.group(2).lower()}"
                f"-collection-calendar/"
                if round_match
                else None
            )
            candidates.append(
                {
                    "address": _clean(cells[0].get_text(" ")),
                    "calendar_url": calendar_url,
                }
            )
    else:
        for details in soup.find_all("details"):
            summary = details.find("summary")
            link = details.find("a", href=lambda h: h and "collection-calendar" in h)
            candidates.append(
                {
                    "address": _clean((summary or details).get_text(" ")),
                    "calendar_url": (
                        requests.compat.urljoin(base, link["href"]) if link else None
                    ),
                }
            )
    return candidates


def _match_address(candidates, paon):
    """Return the one candidate whose address starts with `paon` as a whole word.

    "1" matches "1 High St" but not "11 High St" or "1A High St"; "1 High St"
    matches "1 High St, Chelmsford, CM1 1AA". Raises ValueError, listing the
    candidates, when no address or more than one address matches.
    """
    check_paon(paon)
    wanted = _clean(paon)
    pattern = re.compile(rf"{re.escape(wanted)}(?!\w)", re.IGNORECASE)
    seen, unique = set(), []
    for c in candidates:
        if c["address"].lower() not in seen:
            seen.add(c["address"].lower())
            unique.append(c)
    matches = [c for c in unique if pattern.match(c["address"])]
    if len(matches) == 1:
        return matches[0]
    listing = (
        "\n".join(f"  - {c['address']}" for c in (matches or unique)) or "  (none)"
    )
    if matches:
        raise ValueError(
            f"House number '{paon}' matches {len(matches)} addresses, please be more "
            f"specific (e.g. include the street name):\n{listing}"
        )
    raise ValueError(
        f"No address starting with '{paon}' was found for this postcode. "
        f"Addresses found:\n{listing}"
    )


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
                link for the identified round can't be located, or `paon` doesn't match exactly
                one address (start of the address, whole word) in the search results.
        """
        try:
            data = {"bins": []}
            postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")

            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
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

            # Step 3: pick the single result whose address starts with `paon`.
            candidates = _extract_candidates(soup)
            match = _match_address(candidates, user_paon)
            calendar_url = match["calendar_url"]
            if calendar_url is None:
                raise ValueError(
                    f"Found address '{match['address']}' but no collection round "
                    f"for it on the council's page"
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
                                "collectionDate": collection_date.strftime(date_format),
                            }
                        )
        except Exception as e:
            print(f"An error occurred: {e}")
            raise

        return data
