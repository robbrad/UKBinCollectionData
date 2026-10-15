"""North East Derbyshire District Council.

The council withdrew the per-address lookup from its self-service portal
(#1881): `Check_your_Bin_Day` now redirects to the homepage, so the old
Selenium uprn + postcode scraper can never succeed. The district's
collection calendars are instead published as plain HTML on the council
website, as two area calendars -- "Calendar A - The North" and
"Calendar B - The South" -- each a list of date ranges and the bins
collected during that range, e.g.

    Monday 30th November to Friday 4th December 2026:
        Green Bin, Burgundy Bin and Food Caddy collections

A week-long range says which bins go out that week but not on which day
*your* bin goes out, so the user has to supply two things: their area and
their normal collection weekday. Both are passed in the house number
field, separated by a comma, e.g. "North, Monday" or "Clay Cross, Friday".
See the wiki note in input.json.
"""

import re
from datetime import date, datetime, timedelta

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import (
    date_format,
    get_scraper_user_agent,
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

CALENDAR_URL = (
    "https://www.ne-derbyshire.gov.uk/bins-and-recycling/bin-collection-dates"
)

# The two collection-date panels, as the council's accordion markup keys them,
# and the anchors on the two "Which calendar do I use?" settlement lists.
PANEL_IDS = {
    "north": "rlta-panel-view-the-north-area-upcoming-collection-dates",
    "south": "rlta-panel-view-the-south-area-upcoming-collection-dates",
}
SETTLEMENT_ANCHORS = {"north": "north", "south": "south"}

MONTHS = {
    month.lower(): number
    for number, month in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        start=1,
    )
}

# Normal collection days only: the district collects Monday to Friday, and a
# Saturday date only ever arises as a bank-holiday week's shifted Friday.
WEEKDAYS = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tues": 1,
    "tue": 1,
    "wednesday": 2,
    "weds": 2,
    "wed": 2,
    "thursday": 3,
    "thurs": 3,
    "thur": 3,
    "thu": 3,
    "friday": 4,
    "fri": 4,
}
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# Bin types, matched against the entry text with every non-letter removed, so
# that the council's occasional typos ("B lack Bin") still match.
BIN_KEYWORDS = [
    ("blackbin", "Black Bin"),
    ("burgundy", "Burgundy Bin"),
    ("greenbin", "Green Bin"),
    ("foodcaddy", "Food Caddy"),
]

# A month heading: "August 2026", "December '26", "January 27".
MONTH_HEADING_RE = re.compile(r"^(?P<month>[A-Za-z]+)\s*'?(?P<year>\d{2}|\d{4})$")
# One date in a range: weekday, ordinal day, and optionally a month and a year.
# The month is omitted on the first date of a same-month range ("Monday 3rd to
# Friday 7th August") and the year is often carried by the month heading alone.
DATE_RE = re.compile(
    r"(?P<weekday>[A-Za-z]+)\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?"
    r"(?:\s+(?P<month>[A-Za-z]+))?"
    r"(?:\s+(?P<year>\d{4}))?"
)
MONDAY = 0


def _norm(text: str) -> str:
    """Collapse the council CMS's whitespace into single spaces."""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _full_year(value: str) -> int:
    """Expand the council's two-digit years ("'26") to four digits."""
    year = int(value)
    return year + 2000 if year < 100 else year


def _month_context(text: str):
    """Return (month, year) if text is a month heading such as "August 2026"."""
    match = MONTH_HEADING_RE.match(text)
    if not match:
        return None
    month = MONTHS.get(match.group("month").lower())
    if month is None:
        return None
    return month, _full_year(match.group("year"))


def _infer_year(month: int, day: int, today: date) -> int:
    """Pick the year that puts an undated entry closest to today.

    Only reached when neither the entry nor a month heading carries a year,
    which the live page never does; it keeps a CMS edit from silently
    throwing a whole month into the wrong year.
    """
    candidates = []
    for year in (today.year - 1, today.year, today.year + 1):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            continue  # e.g. 29 February in a non-leap year
    if not candidates:
        return today.year
    return min(candidates, key=lambda day_in_year: abs((day_in_year - today).days)).year


def _parse_date_part(part: str):
    """Pull (day, month, year) out of one side of a range; month/year optional."""
    match = DATE_RE.search(part)
    if not match:
        return None
    month = match.group("month")
    return (
        int(match.group("day")),
        MONTHS.get(month.lower()) if month else None,
        int(match.group("year")) if match.group("year") else None,
    )


def _parse_range(date_text: str, context, today: date):
    """Parse an entry's date text into (start, end) dates.

    `context` is the (month, year) of the entry's month heading, or None.
    A single date gives start == end.
    """
    halves = re.split(r"\s+to\s+", date_text, maxsplit=1)
    end_part = _parse_date_part(halves[-1])
    if end_part is None:
        return None
    end_day, end_month, end_year = end_part

    context_month, context_year = context if context else (None, None)
    if end_month is None:
        end_month = context_month
    if end_month is None:
        return None
    if end_year is None:
        end_year = context_year or _infer_year(end_month, end_day, today)

    if len(halves) == 1:
        start_day, start_month, start_year = end_day, end_month, end_year
    else:
        start_part = _parse_date_part(halves[0])
        if start_part is None:
            return None
        start_day, start_month, start_year = start_part
        if start_month is None:
            start_month = end_month
        if start_year is None:
            # A range that crosses New Year ("Monday 28th December to Friday
            # 1st January 2027") carries a year on its end date only.
            start_year = end_year - 1 if start_month > end_month else end_year

    try:
        start = date(start_year, start_month, start_day)
        end = date(end_year, end_month, end_day)
    except ValueError:
        return None
    return (start, end) if start <= end else None


def _bins_in(text: str):
    """Bin types named in an entry, in the order this module lists them."""
    compact = re.sub(r"[^a-z]", "", text.lower())
    return [name for keyword, name in BIN_KEYWORDS if keyword in compact]


def _collection_dates(start: date, end: date, weekday: int):
    """Dates in [start, end] on which a `weekday` household is collected.

    Normally that is every matching weekday in the range, which also covers
    ranges spanning several weeks and weeks split across two monthly sections
    ("Monday 28th to Wednesday 30th September" followed by "Thursday 1st to
    Friday 2nd October").

    A full week whose range starts after Monday is a bank-holiday week: the
    council shifts *every* household by the same number of days ("when there
    is a Bank Holiday Monday, the collection day is normally one day later
    than usual"), so a Tuesday-to-Saturday range collects a Monday household
    on the Tuesday and a Friday household on the Saturday.
    """
    if (end - start).days + 1 >= 5 and start.weekday() != MONDAY:
        shifted = start + timedelta(days=weekday)
        return [shifted] if shifted <= end else []

    first = start + timedelta(days=(weekday - start.weekday()) % 7)
    if first > end:
        return []
    return [
        first + timedelta(days=7 * week)
        for week in range(((end - first).days // 7) + 1)
    ]


def _settlements(soup: BeautifulSoup, area: str):
    """Settlement names listed under the "Which calendar do I use?" heading."""
    anchor = soup.find("a", id=SETTLEMENT_ANCHORS[area])
    heading = anchor.find_parent(["h2", "h3", "h4"]) if anchor else None
    listing = heading.find_next("ul") if heading else None
    if listing is None:
        return set()
    names = set()
    for item in listing.find_all("li"):
        # "Sutton (smaller 'rural' route vehicle)" -> "sutton"
        name = _norm(re.sub(r"\(.*?\)", "", item.get_text(" ", strip=True)))
        if name:
            names.add(name.lower())
    return names


def _resolve_area(wanted: str, soup: BeautifulSoup) -> str:
    """Map an area or settlement name onto "north" or "south"."""
    wanted = wanted.strip().lower()
    if wanted in PANEL_IDS:
        return wanted

    areas = {area: _settlements(soup, area) for area in PANEL_IDS}
    matches = sorted(area for area, names in areas.items() if wanted in names)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            f"'{wanted.title()}' is on both of North East Derbyshire's "
            "calendars, because its smaller 'rural' route properties are on "
            "Calendar A (North) and the rest on Calendar B (South). Pass "
            "'North' or 'South' in place of the settlement name, e.g. "
            f"'North, Monday' -- check which applies to you on {CALENDAR_URL}."
        )

    known = sorted(name.title() for names in areas.values() for name in names)
    raise ValueError(
        f"'{wanted.title()}' is not a North East Derbyshire collection area. "
        "Pass 'North' or 'South', or one of these settlements: "
        f"{', '.join(known) if known else '(none listed on the page)'}."
    )


def _parse_user_input(paon, soup: BeautifulSoup):
    """Split the house number field into (area, weekday index)."""
    if not paon or not str(paon).strip():
        raise ValueError(
            "North East Derbyshire needs your collection area and your normal "
            "collection weekday in the house number field, separated by a "
            "comma, e.g. 'North, Monday' or 'Clay Cross, Friday'."
        )

    parts = [part.strip() for part in re.split(r"[,;/]", str(paon)) if part.strip()]
    weekdays = [part for part in parts if part.lower() in WEEKDAYS]
    areas = [part for part in parts if part.lower() not in WEEKDAYS]

    if len(weekdays) != 1 or len(areas) != 1:
        raise ValueError(
            f"Could not read '{paon}' as an area and a weekday. Pass both in "
            "the house number field, separated by a comma, e.g. 'North, "
            "Monday' or 'Clay Cross, Friday'. Accepted weekdays: "
            f"{', '.join(WEEKDAY_NAMES)}."
        )

    return _resolve_area(areas[0], soup), WEEKDAYS[weekdays[0].lower()]


def parse_calendar(html: str, paon, today=None) -> dict:
    """Parse the calendar page for one area and collection weekday.

    Kept separate from `parse_data` so the parsing is testable offline.
    """
    today = today or datetime.now().date()
    soup = BeautifulSoup(html, "html.parser")
    area, weekday = _parse_user_input(paon, soup)

    panel = soup.find("div", id=PANEL_IDS[area])
    if panel is None:
        raise ValueError(
            f"Could not find the {area} collection dates on {CALENDAR_URL}. "
            "The council may have changed the page."
        )

    collections = set()
    context = None
    for element in panel.find_all(["h4", "p", "li"]):
        text = _norm(element.get_text(" ", strip=True))
        if not text:
            continue

        heading = _month_context(text)
        if heading:
            context = heading
            continue

        date_text, _, detail = text.partition(":")
        if not detail or "no collections" in text.lower():
            continue
        bins = _bins_in(detail)
        if not bins:
            continue
        span = _parse_range(date_text, context, today)
        if span is None:
            continue

        for collection_date in _collection_dates(span[0], span[1], weekday):
            if collection_date >= today:
                for bin_type in bins:
                    collections.add((collection_date, bin_type))

    if not collections:
        raise ValueError(
            f"No upcoming {area} collections found for "
            f"{WEEKDAY_NAMES[weekday]} on {CALENDAR_URL}. The published "
            "calendar may have run out and need extending by the council."
        )

    return {
        "bins": [
            {"type": bin_type, "collectionDate": collection_date.strftime(date_format)}
            for collection_date, bin_type in sorted(collections)
        ]
    }


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        url = kwargs.get("url") or CALENDAR_URL
        response = requests.get(
            url,
            headers={"User-Agent": get_scraper_user_agent()},
            timeout=60,
        )
        response.raise_for_status()
        return parse_calendar(response.text, kwargs.get("paon"))
