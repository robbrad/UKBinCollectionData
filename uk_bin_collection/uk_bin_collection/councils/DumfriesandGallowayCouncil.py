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
        Fetch upcoming bin collections for a property and return them as structured data.
        
        Parses an ICS calendar URL constructed from the provided `uprn` to collect events occurring within the next 60 days and returns each collection entry with its type and formatted collection date.
        
        Parameters:
            uprn (str): Unique Property Reference Number used to build the council's ICS calendar URL.
        
        Returns:
            dict: A dictionary with a single key `"bins"` containing a list of collection records. Each record is a dict with:
                - "type" (str): Collection type/name.
                - "collectionDate" (str): Collection date formatted according to `date_format`.
        """
        driver = None
        try:
            data = {"bins": []}

            user_uprn = kwargs.get("uprn")
            check_uprn(user_uprn)

            ics_url = f"https://www.dumfriesandgalloway.gov.uk/bins-recycling/waste-collection-schedule/download/{user_uprn}"

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