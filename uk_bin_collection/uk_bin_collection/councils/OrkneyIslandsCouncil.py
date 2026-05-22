import base64
import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    BASE_URL = "https://www.orkney.gov.uk/our-services/waste-and-recycling/household-waste-and-recycling/"

    def parse_data(self, page: str, **kwargs) -> dict:
        user_paon = kwargs.get("paon")
        if not user_paon:
            raise ValueError(
                "A street name or area name is required (paon parameter). "
                "Search at https://www.orkney.gov.uk/mybins to find your area."
            )

        bindata = {"bins": []}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
        }

        session = requests.Session()
        session.headers.update(headers)

        # Step 1: Search the FAQ system with the street/area name.
        # The MyBins page is a Jadu FAQ module. Searching with
        # faqsearchOperator=AND matches the phrase within FAQ answers
        # which list the streets covered by each collection area.
        search_url = self.BASE_URL
        response = session.get(
            search_url,
            params={
                "faqsearch": user_paon,
                "faqsearchOperator": "AND",
            },
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Check if we landed directly on a single result (FAQ detail page)
        # or got a list of matching areas. A detail page has .faq-detail
        # with .faq-answer-detail inside; a list page has multiple links
        # with ?id= params.
        faq_detail = soup.find("div", class_="faq-answer-detail")
        if faq_detail:
            # Single result -- we're already on the detail page
            return self._parse_faq_detail(faq_detail, session, bindata)

        # Multiple results or search results -- find area links
        result_links = soup.find_all("a", href=re.compile(r"\?id=\d+"))
        if not result_links:
            raise ValueError(
                f"No collection area found for '{user_paon}'. "
                "Try searching with a street name (e.g. 'Albert Street') "
                "or island name (e.g. 'Sanday'). Check your area at "
                "https://www.orkney.gov.uk/mybins"
            )

        # Use the first matching result
        first_link = result_links[0]
        href = first_link.get("href", "")
        faq_id = re.search(r"\?id=(\d+)", href)
        if not faq_id:
            raise ValueError("Could not extract FAQ ID from search results.")

        # Step 2: Fetch the FAQ detail page for the matched area
        detail_url = f"{self.BASE_URL}?id={faq_id.group(1)}"
        response = session.get(detail_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        faq_detail = soup.find("div", class_="faq-answer-detail")
        if not faq_detail:
            raise ValueError(
                "Could not find collection details on the area page."
            )

        return self._parse_faq_detail(faq_detail, session, bindata)

    def _parse_faq_detail(
        self,
        faq_detail,
        session: requests.Session,
        bindata: dict,
    ) -> dict:
        """Parse a FAQ detail page. Two formats exist:
        - Mainland areas (01-15): embedded Google Calendar iframe with
          actual dated events via iCal feed.
        - Island areas: plain text saying 'Your collection day is <Day>.'
        """

        # Try to find a Google Calendar embed (mainland areas)
        # The calendar ID is in the iframe src or the print link's
        # data-calendar-source attribute (base64-encoded).
        calendar_id = self._extract_calendar_id(faq_detail)
        if calendar_id:
            return self._parse_google_calendar(calendar_id, session, bindata)

        # Fall back to island format: "Your collection day is <Day>."
        return self._parse_island_day(faq_detail, bindata)

    def _extract_calendar_id(self, faq_detail) -> str:
        """Extract the Google Calendar ID from the FAQ detail HTML.
        Looks for the data-calendar-source attribute on the print link
        first, then falls back to parsing the iframe src parameter.
        """

        # Method 1: data-calendar-source attribute (base64-encoded cal ID)
        print_link = faq_detail.find("a", class_="calendarLink")
        if print_link and print_link.get("data-calendar-source"):
            try:
                return base64.b64decode(
                    print_link["data-calendar-source"]
                ).decode("utf-8")
            except Exception:
                pass

        # Method 2: Parse the print link href for the src= parameter
        if print_link and print_link.get("href"):
            parsed = urlparse(print_link["href"])
            params = parse_qs(parsed.query)
            src_list = params.get("src", [])
            if src_list:
                try:
                    return base64.b64decode(src_list[0]).decode("utf-8")
                except Exception:
                    pass

        # Method 3: Parse the iframe src for the src= parameter
        iframe = faq_detail.find("iframe")
        if iframe and iframe.get("src"):
            parsed = urlparse(iframe["src"])
            params = parse_qs(parsed.query)
            src_list = params.get("src", [])
            if src_list:
                try:
                    return base64.b64decode(src_list[0]).decode("utf-8")
                except Exception:
                    pass

        return ""

    def _parse_google_calendar(
        self,
        calendar_id: str,
        session: requests.Session,
        bindata: dict,
    ) -> dict:
        """Fetch the public iCal feed for a Google Calendar and parse
        the VEVENT entries into bin collection dates."""

        ical_url = (
            f"https://calendar.google.com/calendar/ical/"
            f"{calendar_id}/public/basic.ics"
        )
        response = session.get(ical_url)
        response.raise_for_status()

        ical_text = response.text
        now = datetime.now()

        # Parse VEVENT blocks from the iCal data.
        # Events use RRULE for recurring collections and may have
        # EXDATE entries for skipped weeks (e.g. Christmas).
        # We expand recurrences manually for the next ~6 months.
        events = self._expand_ical_events(ical_text, now)

        for event_date, summary in events:
            # Strip the "Area XX - " prefix for cleaner bin type names
            bin_type = re.sub(r"^Area \d+ - ", "", summary).strip()
            if not bin_type:
                continue

            bindata["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": event_date.strftime(date_format),
                }
            )

        if not bindata["bins"]:
            raise ValueError(
                "No upcoming collection dates found in the calendar. "
                "The council may not have published schedules yet."
            )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(
                x.get("collectionDate"), date_format
            )
        )

        return bindata

    def _expand_ical_events(
        self, ical_text: str, now: datetime
    ) -> list:
        """Parse iCal text and expand recurring events into concrete
        (date, summary) tuples for the next 6 months from now.

        Handles:
        - Single events (DTSTART;VALUE=DATE)
        - Recurring events (RRULE with FREQ=WEEKLY, INTERVAL, BYDAY)
        - Exception dates (EXDATE;VALUE=DATE)
        - Recurrence overrides (RECURRENCE-ID)
        """
        from datetime import timedelta

        horizon = now + timedelta(days=180)
        results = []

        # Split into VEVENT blocks
        vevent_pattern = re.compile(
            r"BEGIN:VEVENT\r?\n(.*?)END:VEVENT", re.DOTALL
        )

        # First pass: collect recurrence overrides (events with
        # RECURRENCE-ID that replace a specific occurrence)
        overrides = {}
        for match in vevent_pattern.finditer(ical_text):
            block = match.group(1)
            if "RECURRENCE-ID" not in block:
                continue
            uid = self._ical_field(block, "UID")
            rec_date = self._ical_date(block, "RECURRENCE-ID")
            summary = self._ical_field(block, "SUMMARY")
            dtstart = self._ical_date(block, "DTSTART")
            if uid and rec_date:
                overrides[(uid, rec_date)] = (dtstart or rec_date, summary)

        # Second pass: process base events
        for match in vevent_pattern.finditer(ical_text):
            block = match.group(1)
            if "RECURRENCE-ID" in block:
                continue

            uid = self._ical_field(block, "UID")
            summary = self._ical_field(block, "SUMMARY")
            dtstart = self._ical_date(block, "DTSTART")
            if not dtstart or not summary:
                continue

            # Collect EXDATE values (excluded dates)
            exdates = set()
            for line in block.split("\n"):
                line = line.strip()
                if line.startswith("EXDATE"):
                    date_val = self._parse_date_value(
                        line.split(":", 1)[-1].strip()
                    )
                    if date_val:
                        exdates.add(date_val)

            rrule_line = self._ical_field(block, "RRULE")
            if rrule_line:
                # Parse RRULE parameters
                rrule_params = {}
                for part in rrule_line.split(";"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        rrule_params[k] = v

                freq = rrule_params.get("FREQ", "")
                interval = int(rrule_params.get("INTERVAL", "1"))

                if freq == "WEEKLY":
                    step = timedelta(weeks=interval)
                    current = dtstart

                    while current <= horizon:
                        if current >= now and current not in exdates:
                            # Check for override
                            override = overrides.get((uid, current))
                            if override:
                                o_date, o_summary = override
                                if o_date and o_date >= now:
                                    results.append(
                                        (o_date, o_summary or summary)
                                    )
                            else:
                                results.append((current, summary))
                        current += step
                else:
                    # Non-weekly recurrence (unlikely for Orkney)
                    if now <= dtstart <= horizon:
                        results.append((dtstart, summary))
            else:
                # Single (non-recurring) event
                if now <= dtstart <= horizon:
                    # Check for override
                    override = overrides.get((uid, dtstart))
                    if override:
                        o_date, o_summary = override
                        if o_date and o_date >= now:
                            results.append((o_date, o_summary or summary))
                    else:
                        results.append((dtstart, summary))

        # Also add any overrides whose base events may have already
        # been processed but the override date is in our window
        # (these are handled above, but standalone overrides for
        # past base events won't be caught)
        for (uid, rec_date), (o_date, o_summary) in overrides.items():
            if o_date and now <= o_date <= horizon:
                # Only add if not already present
                if not any(d == o_date and s == o_summary for d, s in results):
                    results.append((o_date, o_summary))

        return sorted(results, key=lambda x: x[0])

    def _ical_field(self, block: str, field_name: str) -> str:
        """Extract a simple iCal field value, handling fields with
        parameters (e.g. DTSTART;VALUE=DATE:20241209) and iCal line
        folding (continuation lines starting with a space/tab).
        Also unescapes iCal backslash sequences."""
        lines = block.split("\n")
        result = None
        for i, line in enumerate(lines):
            stripped = line.rstrip("\r")
            if result is not None:
                # Check for continuation line (starts with space or tab)
                if stripped.startswith(" ") or stripped.startswith("\t"):
                    result += stripped[1:]
                    continue
                else:
                    break
            if stripped.startswith(field_name):
                result = stripped.split(":", 1)[-1]

        if result is None:
            return ""

        # Unescape iCal sequences: \, -> , and \n -> newline
        result = result.replace("\\,", ",").replace("\\n", "\n")
        return result.strip()

    def _ical_date(self, block: str, field_name: str):
        """Extract a date from an iCal field, returning a datetime
        object or None."""
        raw = self._ical_field(block, field_name)
        return self._parse_date_value(raw)

    def _parse_date_value(self, raw: str):
        """Parse a raw iCal date value like '20241209' or
        '20241209T000000Z' into a datetime."""
        if not raw:
            return None
        # Strip any trailing whitespace/carriage returns
        raw = raw.strip().replace("\r", "")
        try:
            if len(raw) == 8:
                return datetime.strptime(raw, "%Y%m%d")
            elif "T" in raw:
                return datetime.strptime(raw[:8], "%Y%m%d")
            else:
                return datetime.strptime(raw[:8], "%Y%m%d")
        except ValueError:
            return None

    def _parse_island_day(self, faq_detail, bindata: dict) -> dict:
        """Parse island-format FAQ answers that just state a collection
        day name (e.g. 'Your collection day is Thursday.')."""

        text = faq_detail.get_text(" ", strip=True)

        # Look for "Your collection day is <DayName>"
        day_match = re.search(
            r"collection day is\s+(\w+)", text, re.IGNORECASE
        )
        if not day_match:
            raise ValueError(
                "Could not determine collection day from the page. "
                "This area may use a format not yet supported."
            )

        day_name = day_match.group(1).strip()

        # Validate it's a real day name
        if day_name not in days_of_week:
            raise ValueError(
                f"Unrecognised collection day: '{day_name}'."
            )

        # Island collections are general waste only (single stream).
        # The council page doesn't specify bin types for islands --
        # they have a single weekly collection.
        collection_date = get_next_day_of_week(day_name)

        bindata["bins"].append(
            {
                "type": "General Waste",
                "collectionDate": collection_date,
            }
        )

        return bindata
