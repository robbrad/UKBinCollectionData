import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

API_URL = "https://www.merthyr.gov.uk/umbraco/Surface/BinDaySurface/GetCollectionDay"

DAYS_OF_WEEK = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def _next_occurrence(day_name: str) -> datetime:
    """Return the next occurrence of *day_name* (today excluded)."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    target_idx = DAYS_OF_WEEK.index(day_name)
    today_idx = today.weekday()
    days_ahead = (target_idx - today_idx) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def _next_fortnightly(
    day_name: str, current_week: str, bin_week: str
) -> datetime:
    """Return the next fortnightly collection date.

    The council alternates week "one" and week "two" on a Mon-Sun
    boundary.  *current_week* is what the API reports for today.
    *bin_week* is the week this particular bin type collects in.

    Strategy:
        1. Find the next occurrence of *day_name* (today excluded).
        2. Decide whether that date falls in the current week (same
           Mon-Sun span as today) or the following week.
        3. Same-week occurrence keeps the current week label;
           next-week occurrence flips it.
        4. If the label matches *bin_week* -- use it; otherwise add 7.
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    target_idx = DAYS_OF_WEEK.index(day_name)
    today_idx = today.weekday()

    days_ahead = (target_idx - today_idx) % 7
    if days_ahead == 0:
        days_ahead = 7  # skip today

    # Does the candidate fall in the same Mon-Sun week as today?
    in_same_week = (today_idx + days_ahead) <= 6  # still within weekday 0-6
    if in_same_week:
        candidate_week = current_week
    else:
        candidate_week = "two" if current_week == "one" else "one"

    if candidate_week != bin_week:
        days_ahead += 7  # skip to the correct fortnightly week

    return today + timedelta(days=days_ahead)


class CouncilClass(AbstractGetBinDataClass):
    """
    Merthyr Tydfil County Borough Council bin collections.

    Uses the council's Umbraco AJAX endpoint which accepts a postcode
    and returns an HTML fragment with collection day names and a
    week-one / week-two fortnightly indicator.

    Resolution: postcode only (UPRN and house number are ignored --
    the API resolves by postcode area).
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        postcode = kwargs.get("postcode")
        check_postcode(postcode)

        bindata = {"bins": []}

        resp = requests.post(
            API_URL,
            data={"postcode": postcode},
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/134.0.0.0 Safari/537.36"
                ),
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.merthyr.gov.uk/resident/bins-and-recycling/check-your-collection-day/",
            },
            timeout=30,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Check for "No results"
        h4 = soup.find("h4")
        if h4 and "No results" in h4.get_text():
            return bindata

        # Determine current week (one or two)
        h5 = soup.find("h5")
        if not h5:
            raise ValueError(
                "Could not determine current week from Merthyr response"
            )
        current_week_strong = h5.find("strong")
        if not current_week_strong:
            raise ValueError(
                "Could not parse current week indicator"
            )
        current_week = current_week_strong.get_text(strip=True).lower()

        # Parse each <p> for collection info
        for p_tag in soup.find_all("p"):
            text = p_tag.get_text()
            strong_tags = p_tag.find_all("strong")

            if not strong_tags:
                continue

            # Extract day name (always the first <strong>)
            day_name = strong_tags[0].get_text(strip=True)
            if day_name not in DAYS_OF_WEEK:
                continue

            # Determine bin type from the surrounding text
            text_lower = text.lower()
            if "recycling" in text_lower:
                bin_type = "Recycling"
            elif "household waste" in text_lower:
                bin_type = "Household Waste"
            elif "garden waste" in text_lower:
                bin_type = "Garden Waste"
            else:
                # Unknown type -- use the text before "collection day"
                match = re.match(r"Your (.+?) collection day", text)
                bin_type = match.group(1).strip().title() if match else "Unknown"

            # Determine frequency
            if "every week" in text_lower:
                # Weekly collection -- return next 4 occurrences
                base = _next_occurrence(day_name)
                for i in range(4):
                    collection_date = base + timedelta(weeks=i)
                    bindata["bins"].append({
                        "type": bin_type,
                        "collectionDate": collection_date.strftime(date_format),
                    })
            else:
                # Fortnightly -- determine which week this bin collects in
                bin_week_strong = strong_tags[-1] if len(strong_tags) > 1 else None
                if not bin_week_strong:
                    continue
                bin_week = bin_week_strong.get_text(strip=True).lower()

                base = _next_fortnightly(day_name, current_week, bin_week)
                for i in range(2):
                    collection_date = base + timedelta(weeks=i * 2)
                    bindata["bins"].append({
                        "type": bin_type,
                        "collectionDate": collection_date.strftime(date_format),
                    })

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )

        return bindata
