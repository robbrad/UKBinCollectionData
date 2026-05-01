import re
import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://www.thurrock.gov.uk/household-bin-collection-days"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

HEADERS = {
    "User-Agent": "UKBinCollectionData/1.0 (+https://github.com/robbrad/UKBinCollectionData)"
}

LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWY")


def _extract_street_from_paon(paon):
    """Extract street name from paon if it contains more than just a number."""
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
        return street, None
    # Use postcodes.io to get lat/lng, then Nominatim reverse to get street + town
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
                    town = addr.get("town") or addr.get("city") or addr.get("village")
                    if road:
                        return road, town
    except Exception:
        pass
    return None, None


def _get_page_url(letter):
    """Get the URL for a Thurrock street listing page."""
    if letter == "A":
        return f"{BASE_URL}/street-names"
    return f"{BASE_URL}/street-names-{letter.lower()}"


def _scrape_street_page(letter):
    """Scrape a single alphabetical page and return list of (street, town, day, round)."""
    url = _get_page_url(letter)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    entries = []
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 3:
            street_town = cells[0].get_text(strip=True)
            day = cells[1].get_text(strip=True)
            round_id = cells[2].get_text(strip=True)
            # Clean non-breaking spaces and control chars
            day = re.sub(r'[^\w]', '', day)
            round_id = re.sub(r'[^\w]', '', round_id)
            # Split street and town
            parts = street_town.rsplit(",", 1)
            street = parts[0].strip()
            town = parts[1].strip() if len(parts) > 1 else ""
            entries.append((street, town, day, round_id))
    return entries


def _find_street(street_name, town_name=None):
    """Search Thurrock street pages for a matching street.
    Returns (day, round) or raises ValueError."""
    if not street_name:
        raise ValueError("No street name provided")

    first_letter = street_name[0].upper()
    if first_letter not in LETTERS:
        first_letter = "A"

    entries = _scrape_street_page(first_letter)
    street_upper = street_name.upper()
    town_upper = town_name.upper() if town_name else None

    # Exact street match with town
    for street, town, day, round_id in entries:
        if street.upper() == street_upper:
            if not town_upper or town_upper in town.upper():
                return day, round_id

    # Partial match — street name contained in entry
    for street, town, day, round_id in entries:
        if street_upper in street.upper() or street.upper() in street_upper:
            if not town_upper or town_upper in town.upper():
                return day, round_id

    # Try without town filter
    for street, town, day, round_id in entries:
        if street.upper() == street_upper:
            return day, round_id

    for street, town, day, round_id in entries:
        if street_upper in street.upper() or street.upper() in street_upper:
            return day, round_id

    raise ValueError(
        f"Street '{street_name}' not found on Thurrock page for letter '{first_letter}'"
    )


class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)

        street_name, town_name = _resolve_street(user_postcode, user_paon)
        if not street_name:
            raise ValueError(
                f"Could not resolve street name for {user_paon}, {user_postcode}"
            )

        day, round_id = _find_street(street_name, town_name)

        days_of_week = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ]
        round_week = ["A", "B"]

        offset_days = days_of_week.index(day)
        round_index = round_week.index(round_id)

        if round_index == 0:
            bluebrown_start = datetime(2025, 11, 17)
            greengrey_start = datetime(2025, 11, 24)
        else:
            greengrey_start = datetime(2025, 11, 17)
            bluebrown_start = datetime(2025, 11, 24)

        bindata = {"bins": []}

        for base_date in get_dates_every_x_days(greengrey_start, 14, 28):
            collection_date = (
                datetime.strptime(base_date, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime(date_format)
            bindata["bins"].append(
                {"type": "Green/Grey Bin", "collectionDate": collection_date}
            )

        for base_date in get_dates_every_x_days(bluebrown_start, 14, 28):
            collection_date = (
                datetime.strptime(base_date, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime(date_format)
            bindata["bins"].append(
                {"type": "Blue Bin", "collectionDate": collection_date}
            )
            bindata["bins"].append(
                {"type": "Brown Bin", "collectionDate": collection_date}
            )

        for base_date in get_dates_every_x_days(greengrey_start, 7, 56):
            collection_date = (
                datetime.strptime(base_date, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime(date_format)
            bindata["bins"].append(
                {"type": "Food Bin", "collectionDate": collection_date}
            )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
