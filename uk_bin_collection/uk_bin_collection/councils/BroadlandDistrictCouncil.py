# This script pulls (in one hit) the data from Broadland District Council Bins Data
# Working command line:
# python collect_data.py BroadlandDistrictCouncil "https://area.southnorfolkandbroadland.gov.uk/FindAddress" -p "NR10 3FD" -n "1 Park View, Horsford, Norfolk, NR10 3FD"
import re
import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            data = {"bins": []}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}

            uprn = kwargs.get("uprn")
            user_paon = kwargs.get("paon")
            postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            url = kwargs.get("url")

            print(
                f"Starting parse_data with parameters: postcode={postcode}, paon={user_paon}"
            )
            print(
                f"Creating webdriver with: web_driver={web_driver}, headless={headless}"
            )

            driver = create_webdriver(web_driver, headless, None, __name__)
            print(f"Navigating to URL: {url}")
            driver.get(url)
            print("Successfully loaded the page")

            # Handle cookie confirmation dialog
            self._handle_cookie_confirmation(driver)

            wait = WebDriverWait(driver, 60)
            post_code_search = wait.until(
                EC.presence_of_element_located((By.ID, "Postcode"))
            )
            post_code_search.send_keys(postcode)

            # Click the Find address button
            print("Looking for 'Find address' button...")
            submit_btn = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//input[@type='submit' and @class='button button--secondary']",
                    )
                )
            )
            print("Clicking button...")
            submit_btn.send_keys(Keys.ENTER)

            # Wait for the address dropdown to appear
            print("Waiting for address dropdown to appear...")
            address_dropdown = wait.until(
                EC.presence_of_element_located((By.ID, "UprnAddress"))
            )
            print("Found address dropdown")

            # Create a Select object for the dropdown
            dropdown_select = Select(address_dropdown)

            # Search for the exact address
            print(f"Looking for address: {user_paon}")

            # Select the address by visible text
            dropdown_select.select_by_visible_text(user_paon)
            print(f"Selected address: {user_paon}")

            print("Looking for submit button after address selection...")
            submit_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit']"))
            )
            print("Clicking button...")
            submit_btn.send_keys(Keys.ENTER)

            print("Waiting for collection details to appear...")
            address_dropdown = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//div[contains(@class, 'card-body')]//h4[contains(text(), 'Your next collections')]",
                    )
                )
            )

            # Make a BS4 object
            print("Parsing page with BeautifulSoup...")
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Initialize current date
            current_date = datetime.now()

            # Process collection details
            print("Looking for collection details in the page...")

            # Find the card-body div that contains the bin collection information
            card_body = soup.find("div", class_="card-body")

            if card_body:
                # Find the "Your next collections" heading
                next_collections_heading = card_body.find(
                    "h4", string="Your next collections"
                )

                if next_collections_heading:
                    # Find all bin collection divs (each with class "my-2")
                    bin_divs = next_collections_heading.find_next_siblings(
                        "div", class_="my-2"
                    )

                    print(f"Found {len(bin_divs)} bin collection divs")

                    for bin_div in bin_divs:
                        # Find the bin type (in a strong tag)
                        bin_type_elem = bin_div.find("strong")
                        if bin_type_elem:
                            bin_type = bin_type_elem.text.strip()

                            # Get the parent element that contains both the bin type and date
                            text_container = bin_type_elem.parent
                            if text_container:
                                # Extract the full text and remove the bin type to get the date part
                                full_text = text_container.get_text(strip=True)
                                date_text = full_text.replace(bin_type, "").strip()

                                # Parse the date
                                bin_date = self._parse_date(date_text)

                        if bin_type and bin_date:
                            dict_data = {"type": bin_type, "collectionDate": bin_date}
                            data["bins"].append(dict_data)
                            print(f"Added bin data: {dict_data}")

                # If we don't have data, dump the HTML structure for debugging
                if not data["bins"]:
                    print(
                        "Still no bin data found. Dumping HTML structure for debugging:"
                    )
                    card_bodies = soup.find_all("div", class_="card-body")
                    for i, card in enumerate(card_bodies):
                        print(f"Card body {i+1}:")
                        print(
                            card.prettify()[:500]
                        )  # Print first 500 chars of each card

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            print("Cleaning up webdriver...")
            if driver:
                driver.quit()

        return data

    def _handle_cookie_confirmation(self, driver):
        """
        Handle the cookie confirmation dialog for Broadland District Council website.
        """
        print("Checking for cookie confirmation dialog...")
        wait = WebDriverWait(driver, 10)

        try:
            # Try the specific cookie button ID provided
            print("Looking for the 'Allow all cookies' button...")
            cookie_button = wait.until(
                EC.element_to_be_clickable(
                    (By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
                )
            )
            print("Found 'Allow all cookies' button, clicking...")
            cookie_button.send_keys(Keys.ENTER)
            time.sleep(1)
            print("Cookie confirmation handled successfully")
            return True
        except Exception as e:
            print(f"Could not find or click the specific cookie button: {e}")

            # Try alternative selectors as fallback
            try:
                print("Trying alternative selectors...")
                # Try by class
                cookie_button = driver.find_element(
                    By.CLASS_NAME, "CybotCookiebotDialogBodyButton"
                )
                cookie_button.send_keys(Keys.ENTER)
                time.sleep(1)
                print("Cookie confirmation handled with alternative selector")
                return True
            except Exception as e2:
                print(f"Could not find or click alternative cookie button: {e2}")

                # Try by text content
                try:
                    cookie_button = driver.find_element(
                        By.XPATH, "//button[contains(text(), 'Allow all cookies')]"
                    )
                    cookie_button.send_keys(Keys.ENTER)
                    time.sleep(1)
                    print("Cookie confirmation handled with text-based selector")
                    return True
                except Exception as e3:
                    print(f"Could not find or click text-based cookie button: {e3}")
                    print(
                        "No cookie confirmation dialog found or could not interact with it"
                    )
                    return False

    def _parse_date(self, date_text):
        """Helper method to parse dates in various formats"""
        # First, remove any ordinal indicators (1st, 2nd, 3rd, etc.)
        cleaned_date_text = remove_ordinal_indicator_from_date_string(date_text)

        # Check if the string contains a date
        if not contains_date(cleaned_date_text, fuzzy=True):
            # If no date is found, try the regex approach
            bin_date = None
            date_pattern = r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            date_match = re.search(date_pattern, date_text)
            if date_match:
                day = date_match.group(1)
                month = date_match.group(2)
                month_dict = {
                    "January": 1,
                    "Jan": 1,
                    "February": 2,
                    "Feb": 2,
                    "March": 3,
                    "Mar": 3,
                    "April": 4,
                    "Apr": 4,
                    "May": 5,
                    "June": 6,
                    "Jun": 6,
                    "July": 7,
                    "Jul": 7,
                    "August": 8,
                    "Aug": 8,
                    "September": 9,
                    "Sep": 9,
                    "October": 10,
                    "Oct": 10,
                    "November": 11,
                    "Nov": 11,
                    "December": 12,
                    "Dec": 12,
                }
                month_num = month_dict.get(month)
                if month_num:
                    current_date = datetime.now()
                    year = current_date.year
                    if month_num < current_date.month:
                        year += 1
                    bin_date = f"{int(day):02d}/{month_num:02d}/{year}"
            return bin_date

        # Try common date formats
        date_formats = [
            "%d %B %Y",
            "%d %b %Y",
            "%A %d %B %Y",
            "%A %d %b %Y",
        ]

        for fmt in date_formats:
            try:
                bin_date = datetime.strptime(cleaned_date_text, fmt)
                return bin_date.strftime("%d/%m/%Y")
            except ValueError:
                continue

        # If we get here, we couldn't parse the date with our formats
        # Try to extract it using dateutil's parser as a last resort
        try:
            from dateutil.parser import parse

            parsed_date = parse(cleaned_date_text, fuzzy=True)
            return parsed_date.strftime("%d/%m/%Y")
        except Exception:
            return None
