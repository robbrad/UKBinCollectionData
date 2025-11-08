import re
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from icalevents.icalevents import events
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        """
        Locate the council collection round for the given address and return upcoming bin collection dates and types.
        
        Parses the council bin-collection webpage for the provided postcode and property identifier (paon), determines the matching collection round, fetches the corresponding ICS calendar for the 2025-26 year range, and returns each scheduled collection within the next 60 days as separate entries.
        
        Parameters:
            page (str): Unused parameter retained for API compatibility.
            postcode (str, in kwargs): Postcode to search on the council site.
            paon (str, in kwargs): Property/house name or number used to match the address row.
            web_driver (optional, in kwargs): WebDriver identifier or configuration passed to create_webdriver.
            headless (optional, in kwargs): Headless flag passed to create_webdriver.
        
        Returns:
            dict: A dictionary with a "bins" key containing a list of collection entries. Each entry is a dict with:
                - "type": collection type string (e.g., "General waste")
                - "collectionDate": collection date formatted according to the module's `date_format`
        
        Raises:
            ValueError: If no collection round can be found for the provided `paon`.
        """
        driver = None
        try:
            data = {"bins": []}
            user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"

            postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            wait = WebDriverWait(driver, 30)

            # Navigate to bin collection page
            driver.get(
                "https://www.chelmsford.gov.uk/bins-and-recycling/check-your-collection-day/"
            )

            # Handle cookie overlay
            try:
                accept_btn = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//*[contains(text(), 'ACCEPT')]")
                    )
                )
                accept_btn.click()
                time.sleep(1)
            except Exception as e:
                # Cookie banner not present or already accepted
                pass

            # Find postcode input field (dynamic ID)
            postcode_input = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[contains(@id, '_keyword')]")
                )
            )
            postcode_input.clear()
            postcode_input.send_keys(postcode)

            # Click search button
            submit_btn = wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "__submitButton"))
            )
            submit_btn.click()

            # Wait for results table
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))

            # Get the collection round from the table row
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Find the row containing the address
            for row in soup.find_all("tr"):
                if user_paon in row.get_text():
                    # Extract collection round (e.g., "Tuesday B")
                    row_text = row.get_text()
                    round_match = re.search(
                        r"(Monday|Tuesday|Wednesday|Thursday|Friday)\s+([AB])", row_text
                    )
                    if round_match:
                        day = round_match.group(1).lower()
                        letter = round_match.group(2).lower()
                        ics_url = f"https://www.chelmsford.gov.uk/media/t03c4mik/{day}-{letter}-2025-26.ics"
                        break
            else:
                raise ValueError(
                    f"Could not find collection round for address: {user_paon}"
                )

            # Get events from ICS file within the next 60 days
            now = datetime.now()
            future = now + timedelta(days=60)

            # Parse ICS calendar
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
        finally:
            if driver:
                driver.quit()

        return data