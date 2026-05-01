import re
import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

DIRECTORY_SEARCH = "https://www.edinburgh.gov.uk/directory/search"
DIRECTORY_RECORD = "https://www.edinburgh.gov.uk/directory-record"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

HEADERS = {
    "User-Agent": "UKBinCollectionData/1.0 (+https://github.com/robbrad/UKBinCollectionData)"
}

CALENDAR_CODES = {
    "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
    "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday",
}


def _extract_street_from_paon(paon):
    """Extract street name from paon if it contains more than just a number.
    Handles formats like '157 Morningside Road' or 'Morningside Road'."""
    if not paon:
        return None
    stripped = re.sub(r"^\d+[a-zA-Z]?\s+", "", paon.strip())
    if stripped and stripped != paon.strip():
        return stripped
    if not paon.strip()[0].isdigit():
        return paon.strip()
    return None


def _resolve_street(postcode, paon):
    """Get street name from paon string or via postcode geocode + Nominatim reverse."""
    street = _extract_street_from_paon(paon)
    if street:
        return street
    # Use postcodes.io to get lat/lng, then Nominatim reverse to get street
    try:
        pc_clean = postcode.replace(" ", "")
        pc_resp = requests.get(
            f"https://api.postcodes.io/postcodes/{pc_clean}",
            headers=HEADERS, timeout=10,
        )
        if pc_resp.status_code == 200:
            pc_data = pc_resp.json()
            if pc_data.get("status") == 200 and pc_data.get("result"):
                lat = pc_data["result"]["latitude"]
                lng = pc_data["result"]["longitude"]
                rev_resp = requests.get(
                    NOMINATIM_URL.replace("/search", "/reverse"),
                    params={"lat": lat, "lon": lng, "format": "json", "addressdetails": 1},
                    headers=HEADERS, timeout=10,
                )
                if rev_resp.status_code == 200:
                    addr = rev_resp.json().get("address", {})
                    road = addr.get("road") or addr.get("street")
                    if road:
                        return road
    except Exception:
        pass
    return None


def _search_directory(street_name):
    """Search Edinburgh's waste collection directory for a street name.
    Returns list of (record_url, record_title) tuples."""
    params = {"directoryID": "10251", "keywords": street_name}
    resp = requests.get(DIRECTORY_SEARCH, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for link in soup.select("a.list__link"):
        href = link.get("href", "")
        if "/directory-record/" in href:
            title = link.get_text(strip=True)
            if not href.startswith("http"):
                href = "https://www.edinburgh.gov.uk" + href
            results.append((href, title))
    return results


def _get_calendar_code(record_url):
    """Fetch a directory record page and extract the calendar code."""
    resp = requests.get(record_url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    dts = soup.find_all("dt")
    for dt in dts:
        if "calendar code" in dt.get_text(strip=True).lower():
            dd = dt.find_next_sibling("dd")
            if dd:
                return dd.get_text(strip=True)
    return None


def _parse_calendar_code(code):
    """Parse a calendar code like 'Tue_2' into (day_name, week_index).
    Returns (day_name, week_index) where week_index is 0-based."""
    m = re.match(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)_(\d)", code)
    if not m:
        return None, None
    day_abbr = m.group(1)
    week_num = int(m.group(2))
    day_name = CALENDAR_CODES.get(day_abbr)
    return day_name, week_num - 1


class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)

        street_name = _resolve_street(user_postcode, user_paon)
        if not street_name:
            raise ValueError(
                f"Could not resolve street name for {user_paon}, {user_postcode}"
            )

        records = _search_directory(street_name)
        if not records:
            raise ValueError(
                f"No Edinburgh collection records found for street '{street_name}'"
            )

        # If multiple results, prefer exact match on street name
        best_url = records[0][0]
        street_upper = street_name.upper()
        for url, title in records:
            if title.upper() == street_upper:
                best_url = url
                break

        calendar_code = _get_calendar_code(best_url)
        if not calendar_code:
            raise ValueError(
                f"No calendar code found for '{street_name}' at {best_url}"
            )

        day_name, week_index = _parse_calendar_code(calendar_code)
        if not day_name:
            raise ValueError(f"Could not parse calendar code '{calendar_code}'")

        days_of_week = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ]
        offset_days = days_of_week.index(day_name)

        if week_index == 0:
            recycling_start = datetime(2025, 11, 3)
            glass_start = datetime(2025, 11, 3)
            refuse_start = datetime(2025, 11, 10)
        else:
            recycling_start = datetime(2025, 11, 10)
            glass_start = datetime(2025, 11, 10)
            refuse_start = datetime(2025, 11, 3)

        bindata = {"bins": []}

        for base_date in get_dates_every_x_days(refuse_start, 14, 28):
            collection_date = (
                datetime.strptime(base_date, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime(date_format)
            bindata["bins"].append(
                {"type": "Grey Bin", "collectionDate": collection_date}
            )

        for base_date in get_dates_every_x_days(recycling_start, 14, 28):
            collection_date = (
                datetime.strptime(base_date, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime(date_format)
            bindata["bins"].append(
                {"type": "Green Bin", "collectionDate": collection_date}
            )

        for base_date in get_dates_every_x_days(glass_start, 14, 28):
            collection_date = (
                datetime.strptime(base_date, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime(date_format)
            bindata["bins"].append(
                {"type": "Glass Box", "collectionDate": collection_date}
            )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
