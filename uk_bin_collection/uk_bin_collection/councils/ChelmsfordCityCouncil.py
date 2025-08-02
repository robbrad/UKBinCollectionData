import re
import time
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from icalevents.icalevents import events

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            data = {"bins": []}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}
            
            postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            
            driver = create_webdriver(web_driver, headless, None, __name__)
            wait = WebDriverWait(driver, 30)
            
            # Navigate to bin collection page
            driver.get("https://www.chelmsford.gov.uk/bins-and-recycling/check-your-collection-day/")
            
            # Handle cookie overlay
            try:
                accept_btn = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'ACCEPT')]"))
                )
                accept_btn.click()
                time.sleep(1)
            except:
                pass
            
            # Find postcode input field (dynamic ID)
            postcode_input = wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@id, '_keyword')]"))
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
                    round_match = re.search(r"(Monday|Tuesday|Wednesday|Thursday|Friday)\s+([AB])", row_text)
                    if round_match:
                        day = round_match.group(1).lower()
                        letter = round_match.group(2).lower()
                        ics_url = f"https://www.chelmsford.gov.uk/media/4ipavf0m/{day}-{letter}-calendar.ics"
                        break
            else:
                raise ValueError(f"Could not find collection round for address: {user_paon}")
            
            # Get events from ICS file within the next 60 days
            now = datetime.now()
            future = now + timedelta(days=60)
            
            # Parse ICS calendar
            upcoming_events = events(ics_url, start=now, end=future)
            
            for event in sorted(upcoming_events, key=lambda e: e.start):
                if event.summary and event.start:
                    data["bins"].append({
                        "type": event.summary,
                        "collectionDate": event.start.date().strftime(date_format)
                    })
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        
        return data