import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# Westminster City Council uses a street-based (USRN) collection schedule
# at transact.westminster.gov.uk. The portal returns recurring day/time
# schedules rather than specific future dates. This scraper converts the
# day-of-week schedules into the next concrete collection dates.
#
# Westminster is unusual: most streets have DAILY rubbish collection
# (multiple time windows per day) and weekly recycling. This scraper
# outputs the next 7 days of collection dates for each service type.
#
# USRN resolution:
#   - If "uprn" is provided in input.json, it's used directly as the USRN
#     (backward compatible with manual lookup).
#   - If "postcode" is provided instead, the scraper auto-resolves the USRN:
#     1. postcodes.io -> lat/lng for the postcode
#     2. Nominatim reverse geocode -> street name from coordinates
#     3. Westminster street search dropdown -> USRN for that street
#   - No API keys needed; all services are free and public.
#
# Manual USRN lookup (if needed):
#   1. Visit https://transact.westminster.gov.uk/env/streetsearch.aspx
#   2. Select your street from the dropdown
#   3. After submitting, check the URL for the USRN parameter

# Mapping of abbreviated day names to Python weekday numbers (Monday=0)
DAY_ABBREV_MAP = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

LOOKAHEAD_DAYS = 14

STREET_SEARCH_URL = "https://transact.westminster.gov.uk/env/streetsearch.aspx"
STREET_REPORT_URL = "https://transact.westminster.gov.uk/env/streetreport.aspx"

# Common UK road suffixes to strip for fuzzy matching
_ROAD_SUFFIXES = re.compile(
    r"\b(street|road|lane|avenue|drive|close|court|place|way|"
    r"crescent|terrace|gardens|grove|mews|square|hill|rise|"
    r"row|walk|yard|passage|alley|buildings)\b",
    re.IGNORECASE,
)


def _normalise_street(name: str) -> str:
    """Normalise a street name for fuzzy comparison.
    Strips suffixes, apostrophes, hyphens, and collapses whitespace."""
    s = name.strip().lower()
    s = _ROAD_SUFFIXES.sub("", s)
    s = re.sub(r"['\-]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _resolve_usrn_from_postcode(postcode: str, headers: dict) -> str:
    """Resolve a Westminster USRN from a postcode.

    Pipeline:
      1. postcodes.io  -> lat/lng (free, no key)
      2. Nominatim     -> street name from reverse geocode (free, 1 req/s)
      3. Westminster street search dropdown -> USRN

    Returns the USRN string or raises ValueError on failure.
    """
    # --- Step 1: postcode -> lat/lng via postcodes.io ---
    pc_clean = postcode.strip().upper()
    pc_url = f"https://api.postcodes.io/postcodes/{requests.utils.quote(pc_clean)}"
    pc_resp = requests.get(pc_url, headers=headers, timeout=10)
    pc_resp.raise_for_status()
    pc_data = pc_resp.json()

    if pc_data.get("status") != 200 or not pc_data.get("result"):
        raise ValueError(
            f"postcodes.io could not resolve postcode '{pc_clean}'. "
            f"Check it is a valid Westminster postcode."
        )

    lat = pc_data["result"]["latitude"]
    lng = pc_data["result"]["longitude"]

    # Quick sanity check: admin_district should be Westminster
    district = (pc_data["result"].get("admin_district") or "").lower()
    if "westminster" not in district:
        raise ValueError(
            f"Postcode '{pc_clean}' is in '{pc_data['result'].get('admin_district')}', "
            f"not Westminster. This scraper only covers Westminster City Council."
        )

    # --- Step 2: lat/lng -> street name via Nominatim reverse geocode ---
    nom_url = (
        f"https://nominatim.openstreetmap.org/reverse"
        f"?lat={lat}&lon={lng}&format=json&addressdetails=1&zoom=17"
    )
    nom_resp = requests.get(
        nom_url,
        headers={**headers, "User-Agent": "UKBinCollectionData/1.0"},
        timeout=10,
    )
    nom_resp.raise_for_status()
    nom_data = nom_resp.json()

    road = nom_data.get("address", {}).get("road")
    if not road:
        raise ValueError(
            f"Nominatim could not determine a street name for postcode "
            f"'{pc_clean}' (lat={lat}, lng={lng}). "
            f"Try providing the USRN directly as the uprn parameter."
        )

    # --- Step 3: street name -> USRN via Westminster dropdown ---
    search_resp = requests.get(STREET_SEARCH_URL, headers=headers, timeout=30)
    search_resp.raise_for_status()

    search_soup = BeautifulSoup(search_resp.text, features="html.parser")
    select = search_soup.find("select", {"id": "dlstreets"})
    if not select:
        raise ValueError(
            "Could not find the street dropdown on Westminster's street "
            "search page. The page structure may have changed."
        )

    # Build lookup: normalised name -> (original name, USRN)
    options = {}
    for opt in select.find_all("option"):
        val = opt.get("value", "").strip()
        txt = opt.get_text(strip=True)
        if val and txt:
            options[_normalise_street(txt)] = (txt, val)

    # Try exact match first (normalised)
    road_norm = _normalise_street(road)
    if road_norm in options:
        return options[road_norm][1]

    # Fuzzy: find best substring match
    best_match = None
    best_score = 0
    for key, (orig, usrn) in options.items():
        if not key:
            continue
        # Check if normalised road is a substring or vice versa
        if road_norm in key or key in road_norm:
            score = len(key)
            if score > best_score:
                best_score = score
                best_match = (orig, usrn)

    if best_match:
        return best_match[1]

    # Last resort: match on the first significant word (e.g. "Crawford" matches
    # "Crawford Street", "Crawford Place", "Crawford Mews")
    road_words = [w for w in road_norm.split() if len(w) > 2]
    candidates = []
    for key, (orig, usrn) in options.items():
        if any(w in key for w in road_words):
            candidates.append((orig, usrn))

    if len(candidates) == 1:
        return candidates[0][1]

    if candidates:
        names = ", ".join(c[0] for c in candidates[:5])
        raise ValueError(
            f"Multiple Westminster streets match '{road}': {names}. "
            f"Please provide the USRN directly as the uprn parameter. "
            f"Find it at {STREET_SEARCH_URL}"
        )

    raise ValueError(
        f"Could not find '{road}' in Westminster's street list. "
        f"The street may be too new or named differently. "
        f"Please provide the USRN directly as the uprn parameter. "
        f"Find it at {STREET_SEARCH_URL}"
    )


def _parse_day_list(day_text: str) -> list:
    """
    Parse a day-of-week string from Westminster's schedule tables into a list
    of Python weekday numbers (0=Monday .. 6=Sunday).

    Handles formats like:
      - "Mon - Fri"        -> [0,1,2,3,4]
      - "Sat, Sun"         -> [5,6]
      - "Mon, Wed, Fri"    -> [0,2,4]
      - "Wed"              -> [2]
      - "Mon, Tue, Wed, Thu, Fri" -> [0,1,2,3,4]
    """
    if not day_text or not day_text.strip():
        return []

    text = day_text.strip().lower()

    # Range pattern: "mon - fri" or "mon-fri"
    range_match = re.match(r"^(\w{3})\s*[-–]\s*(\w{3})$", text)
    if range_match:
        start = DAY_ABBREV_MAP.get(range_match.group(1))
        end = DAY_ABBREV_MAP.get(range_match.group(2))
        if start is not None and end is not None:
            if start <= end:
                return list(range(start, end + 1))
            else:
                return list(range(start, 7)) + list(range(0, end + 1))

    # Comma-separated list: "Mon, Wed, Fri"
    days = []
    for part in re.split(r"[,&]+", text):
        part = part.strip()
        inner_range = re.match(r"^(\w{3})\s*[-–]\s*(\w{3})$", part)
        if inner_range:
            start = DAY_ABBREV_MAP.get(inner_range.group(1))
            end = DAY_ABBREV_MAP.get(inner_range.group(2))
            if start is not None and end is not None:
                if start <= end:
                    days.extend(range(start, end + 1))
                else:
                    days.extend(range(start, 7))
                    days.extend(range(0, end + 1))
        else:
            d = DAY_ABBREV_MAP.get(part[:3])
            if d is not None:
                days.append(d)

    return sorted(set(days))


def _next_dates_for_weekdays(weekdays: list, lookahead: int = LOOKAHEAD_DAYS) -> list:
    """
    Return all future dates within the lookahead window that fall on the
    given weekday numbers.
    """
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    dates = []
    for day_offset in range(lookahead):
        check_date = tomorrow + timedelta(days=day_offset)
        if check_date.weekday() in weekdays:
            dates.append(check_date)
    return dates


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        usrn = (kwargs.get("uprn") or "").strip()
        user_postcode = (kwargs.get("postcode") or "").strip()

        bindata = {"bins": []}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36",
        }

        # Resolve USRN: use provided uprn directly, or auto-resolve from postcode
        if usrn:
            pass  # use as-is
        elif user_postcode:
            usrn = _resolve_usrn_from_postcode(user_postcode, headers)
        else:
            raise ValueError(
                "Westminster requires either a USRN (as uprn) or a postcode. "
                "Provide one in input.json."
            )

        url = f"{STREET_REPORT_URL}?USRN={usrn}"

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, features="html.parser")

        # The page has 2-3 tables:
        #   Table 0: Residential rubbish and commercial waste bags
        #   Table 1: Recycling doorstep collections
        #   Table 2: Street cleaning schedule (we skip this)
        tables = soup.find_all("table")

        if not tables:
            raise ValueError(
                f"No collection tables found for USRN {usrn}. "
                f"Check the USRN is correct."
            )

        # Collect (bin_type, weekday_set) pairs, then generate dates
        # Use a dict to merge collection days per service type
        services = {}  # type_name -> set of weekday numbers

        # --- Table 0: Rubbish collections ---
        if len(tables) >= 1:
            rows = tables[0].find_all("tr")[1:]  # skip header
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 5:
                    continue

                weekdays_text = cells[1].get_text(strip=True)
                weekend_text = cells[3].get_text(strip=True)

                all_days = set(
                    _parse_day_list(weekdays_text)
                    + _parse_day_list(weekend_text)
                )

                bin_type = "Rubbish Collection"
                if bin_type not in services:
                    services[bin_type] = set()
                services[bin_type].update(all_days)

        # --- Table 1: Recycling collections ---
        if len(tables) >= 2:
            rows = tables[1].find_all("tr")[1:]  # skip header
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 7:
                    continue

                service_desc = cells[1].get_text(strip=True)
                weekdays_text = cells[3].get_text(strip=True)
                weekend_text = cells[5].get_text(strip=True)

                # Skip business-only collections (blue bag)
                if "business" in service_desc.lower():
                    continue

                all_days = set(
                    _parse_day_list(weekdays_text)
                    + _parse_day_list(weekend_text)
                )

                bin_type = service_desc if service_desc else "Recycling Collection"
                if bin_type not in services:
                    services[bin_type] = set()
                services[bin_type].update(all_days)

        # Generate collection dates for each service type
        seen = set()
        for bin_type, weekday_set in services.items():
            dates = _next_dates_for_weekdays(list(weekday_set))
            for d in dates:
                key = (bin_type, d)
                if key not in seen:
                    seen.add(key)
                    bindata["bins"].append(
                        {
                            "type": bin_type,
                            "collectionDate": d.strftime(date_format),
                        }
                    )

        # Sort by collection date
        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )

        if not bindata["bins"]:
            raise ValueError(
                f"No collection data found for USRN {usrn}. "
                f"This street may not have residential collections."
            )

        return bindata
