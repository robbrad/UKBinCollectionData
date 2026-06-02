import io
import re
from datetime import datetime, timedelta

import pdfplumber
import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# Static PDF URL for the street-sorted bin collection days table.
# Contains ~1240 rows mapping street/town/detail to uplift day and
# recycling calendar week.  Updated in-place by the council; the
# filename has not changed since 2022.
BIN_DAYS_PDF_URL = (
    "https://www.inverclyde.gov.uk/assets/attach/15406/"
    "Bin-Collection-Days-including-HR-T-12.09.22.pdf"
)

# Day-name normalisation (the PDF has "Tues" alongside "Tue", etc.)
DAY_NORMALISE = {
    "mon": "Monday",
    "tue": "Tuesday",
    "tues": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "sun": "Sunday",
    "monday": "Monday",
    "tuesday": "Tuesday",
    "wednesday": "Wednesday",
    "thursday": "Thursday",
    "friday": "Friday",
}

# Reference date for the fortnightly recycling cycle.
# Week 1 recycling falls on the week commencing this date (a Monday).
# Week 2 recycling falls on the alternating week.
# Derived from the 2026-27 recycling calendar PDFs published by the
# council (cyan-shaded weeks = recycling weeks).
WEEK1_RECYCLING_REF = datetime(2026, 3, 16).date()  # Monday


def _day_index(day_name):
    """Return 0=Mon .. 6=Sun for a day name."""
    mapping = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2,
        "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6,
    }
    return mapping.get(day_name)


def _normalise_day(raw):
    """Normalise a short/variant day name to full English name."""
    if not raw:
        return None
    key = raw.strip().lower()
    return DAY_NORMALISE.get(key)


def _is_recycling_week(target_date, recycling_calendar):
    """Return True if target_date falls in a recycling week for the
    given calendar group (1 or 2)."""
    # Both groups alternate fortnightly.  Week 1 recycles on
    # WEEK1_RECYCLING_REF and every 14 days after.
    # Week 2 recycles on the off-weeks (WEEK1_RECYCLING_REF + 7 days).
    ref = WEEK1_RECYCLING_REF
    if recycling_calendar == 2:
        ref = ref + timedelta(days=7)
    # How many days between the reference Monday and the Monday of
    # target_date's week?
    target_monday = target_date - timedelta(days=target_date.weekday())
    delta_days = (target_monday - ref).days
    return delta_days % 14 == 0


def _next_collection_dates(day_name, recycling_calendar, count=8):
    """Return the next `count` collection dates for each bin type.

    Inverclyde runs a fortnightly alternating schedule:
    - Recycling week: Blue bin + Brown bin (garden waste, Mar-Nov only)
    - Residual week:  Black bin + Food waste caddy

    Food waste is collected fortnightly on the same day as the black bin.
    """
    day_idx = _day_index(day_name)
    if day_idx is None:
        return []

    today = datetime.now().date()
    # Find the next occurrence of this weekday (or today if it matches)
    days_ahead = (day_idx - today.weekday()) % 7
    if days_ahead == 0 and datetime.now().hour >= 19:
        days_ahead = 7
    next_day = today + timedelta(days=days_ahead)

    entries = []
    d = next_day
    found = 0
    while found < count:
        is_recycling = _is_recycling_week(d, recycling_calendar)

        if is_recycling:
            entries.append({"date": d, "type": "Blue Recycling Bin"})
            # Brown bin (garden waste) only collected March-November
            if 3 <= d.month <= 11:
                entries.append({"date": d, "type": "Brown Garden Waste Bin"})
        else:
            entries.append({"date": d, "type": "Black General Waste Bin"})
            entries.append({"date": d, "type": "Green Food Waste Caddy"})

        found += 1
        d += timedelta(weeks=1)

    return entries


def _parse_pdf(pdf_bytes):
    """Parse the bin collection days PDF into a list of row dicts."""
    rows = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or not row[0]:
                        continue
                    street = (row[0] or "").strip()
                    if street in ("Street", ""):
                        continue
                    town = (row[1] or "").strip()
                    detail = (row[2] or "").strip()
                    day_raw = (row[3] or "").strip()
                    cal_raw = (row[4] or "").strip()
                    rows.append({
                        "street": street,
                        "town": town,
                        "detail": detail,
                        "day_raw": day_raw,
                        "cal_raw": cal_raw,
                    })
    return rows


def _match_street(rows, street_query, paon=None):
    """Find the best matching row(s) for a street name and optional
    house number/name (paon).

    Returns a list of matching rows, best match first.
    """
    if not street_query:
        return []

    query = street_query.lower().strip()
    # Remove common suffixes that might differ between address formats
    query_words = query.split()

    # Phase 1: exact street name match (case-insensitive)
    exact = [r for r in rows if r["street"].lower() == query]

    # Phase 2: street name contained in query or vice versa
    if not exact:
        exact = [r for r in rows
                 if r["street"].lower() in query
                 or query in r["street"].lower()]

    # Phase 3: match on individual words (drop house number prefix)
    if not exact and len(query_words) > 1:
        # Try dropping the first word (likely a house number) and matching
        street_part = " ".join(query_words[1:])
        exact = [r for r in rows if r["street"].lower() == street_part]
        if not exact:
            exact = [r for r in rows
                     if r["street"].lower() in street_part
                     or street_part in r["street"].lower()]

    if not exact:
        return []

    # If paon provided, try to narrow down by house number in the
    # Detail column or by prioritising rows without detail restrictions
    if paon and len(exact) > 1:
        paon_lower = paon.lower().strip()
        # Check if paon appears in the Detail field
        detail_matches = [r for r in exact
                          if paon_lower in r["detail"].lower()]
        if detail_matches:
            return detail_matches

        # Check if paon is a number and falls within a range in Detail
        paon_num = None
        try:
            paon_num = int(re.match(r"(\d+)", paon_lower).group(1))
        except (AttributeError, ValueError):
            pass

        if paon_num is not None:
            range_matches = []
            for r in exact:
                detail = r["detail"]
                if not detail:
                    continue
                # Parse "X to Y" ranges
                for m in re.finditer(r"(\d+)\s+to\s+(\d+)", detail, re.I):
                    lo, hi = int(m.group(1)), int(m.group(2))
                    if lo <= paon_num <= hi:
                        range_matches.append(r)
                        break
                # Check for individual numbers listed
                nums = set(int(n) for n in re.findall(r"\b(\d+)\b", detail))
                if paon_num in nums:
                    range_matches.append(r)

            if range_matches:
                return range_matches

        # Fall back to rows without detail restrictions (the "general"
        # entry for that street), if any exist alongside detailed ones
        general = [r for r in exact if not r["detail"]]
        if general:
            return general

    return exact


class CouncilClass(AbstractGetBinDataClass):
    """
    Inverclyde Council (Scotland) bin collection scraper.

    The council's GIS noticeboard (maps.inverclyde.gov.uk/noticeboard8/)
    has a broken Cadcorp WML backend as of May 2026 -- both the address
    search and overlay queries return errors.

    This scraper uses the static street-sorted PDF published at
    inverclyde.gov.uk which maps every street to an uplift day and
    recycling calendar week (1 or 2).  The fortnightly alternating
    schedule is then computed from a reference date.

    Input: postcode (required) + paon (house number, recommended).
    The scraper extracts the street name from the postcode by doing a
    reverse lookup via the Kepthouse address API, or the user can pass
    the street name directly as paon.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)

        bindata = {"bins": []}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36",
        }

        # Step 1: Download and parse the bin collection days PDF
        response = requests.get(BIN_DAYS_PDF_URL, headers=headers, timeout=30)
        response.raise_for_status()
        all_rows = _parse_pdf(response.content)

        if not all_rows:
            raise ValueError(
                "Failed to parse bin collection data from PDF."
            )

        # Step 2: Resolve postcode to a street name.
        # The Kepthouse API provides the street; for UKBCD standalone use,
        # we try to extract it from the postcode via Nominatim or the user
        # passes the street name in the paon field.
        street_name = None
        town_name = None

        # Try Nominatim geocoding to get the street name from postcode
        try:
            nominatim_url = (
                "https://nominatim.openstreetmap.org/search"
                "?format=json&countrycodes=gb&limit=1"
                f"&q={user_postcode.replace(' ', '+')}"
            )
            geo_resp = requests.get(
                nominatim_url,
                headers={"User-Agent": "UKBinCollectionData/1.0"},
                timeout=10,
            )
            if geo_resp.status_code == 200 and geo_resp.json():
                display = geo_resp.json()[0].get("display_name", "")
                # display_name format: "PA15 4UE, Greenock, Inverclyde, Scotland, UK"
                # or "Street Name, Town, ..."
                parts = [p.strip() for p in display.split(",")]
                if len(parts) >= 2:
                    # First part might be the postcode or a street name
                    candidate = parts[0]
                    if not re.match(r"^[A-Z]{1,2}\d", candidate):
                        street_name = candidate
                    town_name = parts[1] if len(parts) > 1 else None
        except Exception:
            pass

        # If paon looks like a street name (has letters), use it for matching
        if user_paon and re.search(r"[a-zA-Z]{3,}", user_paon):
            street_name = user_paon

        # If we still have no street name, try to use just paon as a
        # number and match across all streets in the postcode's town
        if not street_name and user_paon:
            # paon is likely just a house number; we need a street name.
            # Try Nominatim with "paon postcode" for a more specific lookup
            try:
                q = f"{user_paon} {user_postcode}".replace(" ", "+")
                geo_resp = requests.get(
                    f"https://nominatim.openstreetmap.org/search"
                    f"?format=json&countrycodes=gb&limit=1&q={q}",
                    headers={"User-Agent": "UKBinCollectionData/1.0"},
                    timeout=10,
                )
                if geo_resp.status_code == 200 and geo_resp.json():
                    display = geo_resp.json()[0].get("display_name", "")
                    parts = [p.strip() for p in display.split(",")]
                    for part in parts:
                        if not re.match(r"^[A-Z]{1,2}\d", part) and \
                           not re.match(r"^\d+$", part) and \
                           part not in ("Inverclyde", "Scotland",
                                        "United Kingdom", "UK"):
                            # Check if this part matches any street in our data
                            test = [r for r in all_rows
                                    if r["street"].lower() == part.lower()]
                            if test:
                                street_name = part
                                break
            except Exception:
                pass

        if not street_name:
            raise ValueError(
                f"Could not determine street name from postcode "
                f"{user_postcode}. Pass the street name as the house "
                f"number/name (paon) parameter, e.g. 'Cartsburn Street'."
            )

        # Step 3: Match the street in the PDF data
        matches = _match_street(all_rows, street_name, user_paon)

        if not matches:
            raise ValueError(
                f"Street '{street_name}' not found in Inverclyde bin "
                f"collection data. Check the street name is correct and "
                f"within the Inverclyde council area."
            )

        # Use the first (best) match
        entry = matches[0]
        day_name = _normalise_day(entry["day_raw"])
        cal_raw = entry["cal_raw"].strip().lower()

        if not day_name:
            # Some entries have split days like "Mon/Fri" -- use the first
            parts = entry["day_raw"].split("/")
            day_name = _normalise_day(parts[0])

        if not day_name:
            raise ValueError(
                f"Could not determine collection day for "
                f"'{street_name}' (raw: '{entry['day_raw']}')."
            )

        # Determine recycling calendar week
        recycling_calendar = None
        if cal_raw in ("1", "1 & 2"):
            recycling_calendar = 1
        elif cal_raw == "2":
            recycling_calendar = 2
        # "no recycling" entries don't get recycling bins

        if recycling_calendar:
            # Generate upcoming collection dates
            entries = _next_collection_dates(day_name, recycling_calendar)
            today = datetime.now().date()
            for e in entries:
                if e["date"] >= today:
                    bindata["bins"].append({
                        "type": e["type"],
                        "collectionDate": e["date"].strftime(date_format),
                    })
        else:
            # No recycling -- only general waste on the given day
            today = datetime.now().date()
            day_idx = _day_index(day_name)
            if day_idx is not None:
                days_ahead = (day_idx - today.weekday()) % 7
                if days_ahead == 0 and datetime.now().hour >= 19:
                    days_ahead = 7
                next_day = today + timedelta(days=days_ahead)
                for week in range(8):
                    d = next_day + timedelta(weeks=week)
                    bindata["bins"].append({
                        "type": "Black General Waste Bin",
                        "collectionDate": d.strftime(date_format),
                    })

        # Check for special recycling day overrides in the Detail field
        # Some addresses have recycling on a different day than residual
        detail = entry["detail"]
        if detail and "recycling collection" in detail.lower():
            # Extract the recycling day from detail text
            day_match = re.search(
                r"recycling\s+collection\s+(?:on\s+)?(\w+)",
                detail, re.I,
            )
            if day_match:
                alt_day = _normalise_day(day_match.group(1))
                if alt_day and alt_day != day_name:
                    # Override recycling dates with the alternative day
                    bindata["bins"] = [
                        b for b in bindata["bins"]
                        if "Recycling" not in b["type"]
                        and "Garden" not in b["type"]
                    ]
                    # Add recycling on the alternative day
                    alt_idx = _day_index(alt_day)
                    if alt_idx is not None and recycling_calendar:
                        today = datetime.now().date()
                        days_ahead = (alt_idx - today.weekday()) % 7
                        if days_ahead == 0 and datetime.now().hour >= 19:
                            days_ahead = 7
                        next_alt = today + timedelta(days=days_ahead)
                        d = next_alt
                        for _ in range(8):
                            if _is_recycling_week(d, recycling_calendar):
                                bindata["bins"].append({
                                    "type": "Blue Recycling Bin",
                                    "collectionDate": d.strftime(date_format),
                                })
                                if 3 <= d.month <= 11:
                                    bindata["bins"].append({
                                        "type": "Brown Garden Waste Bin",
                                        "collectionDate": d.strftime(
                                            date_format
                                        ),
                                    })
                            d += timedelta(weeks=1)

        # Sort by date
        bindata["bins"].sort(
            key=lambda x: datetime.strptime(
                x.get("collectionDate"), date_format
            )
        )

        return bindata
