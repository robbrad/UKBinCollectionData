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
# To find your USRN:
#   1. Visit https://transact.westminster.gov.uk/env/streetsearch.aspx
#   2. Select your street from the dropdown
#   3. After submitting, check the URL for the USRN parameter
#
# Pass the USRN as the "uprn" parameter in input.json.

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
        # Westminster uses USRN (street-level ID), passed via the "uprn" kwarg
        user_usrn = kwargs.get("uprn")
        check_uprn(user_usrn)

        bindata = {"bins": []}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36",
        }

        url = (
            "https://transact.westminster.gov.uk/env/streetreport.aspx"
            f"?USRN={user_usrn}"
        )

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
                f"No collection tables found for USRN {user_usrn}. "
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
                f"No collection data found for USRN {user_usrn}. "
                f"This street may not have residential collections."
            )

        return bindata
