import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from icalevents.icalevents import events

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


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

            # Step 4: fetch the round's calendar page and pull out the .ics link.
            r = session.get(calendar_url, headers=headers, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            a = soup.find("a", href=lambda h: h and h.lower().endswith(".ics"))
            if not a:
                raise ValueError(
                    f"Could not find collection ICS file for address: {user_paon}"
                )
            ics_url = a["href"]

            # Step 5: parse the ICS calendar for events in the next 60 days.
            now = datetime.now()
            future = now + timedelta(days=60)
            upcoming_events = events(ics_url, start=now, end=future)

            for event in sorted(upcoming_events, key=lambda e: e.start):
                if event.summary and event.start:
                    collections = event.summary.split(",")
                    for collection in collections:
                        data["bins"].append(
                            {
                                "type": collection.strip(),
                                "collectionDate": event.start.date().strftime(
                                    date_format
                                ),
                            }
                        )
        except Exception as e:
            print(f"An error occurred: {e}")
            raise

        return data
