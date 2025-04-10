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

from uk_bin_collection.uk_bin_collection.common import (
    contains_date,
    create_webdriver,
    remove_ordinal_indicator_from_date_string,
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete class for Broadland District Council bin collections
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            data = {"bins": []}

            print(
                f"Starting parse_data with parameters: postcode={kwargs.get('postcode')}, paon={kwargs.get('paon')}"
            )

            # Use a realistic user agent to avoid detection
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

            print(
                f"Creating webdriver with: web_driver={web_driver}, headless={headless}, user_agent={user_agent}"
            )
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            url = kwargs.get("url")
            print(f"Navigating to URL: {url}")

            # Add a try-except block specifically for the navigation
            try:
                driver.get(url)
                print("Successfully loaded the page")
                # Add a delay to ensure the page is fully loaded
                time.sleep(2)

                # Handle cookie confirmation dialog
                self._handle_cookie_confirmation(driver)

            except Exception as e:
                print(f"Error loading the page: {e}")
                raise

            wait = WebDriverWait(driver, 60)

            # Find the postcode input field
            print("Looking for postcode input field...")
            try:
                post_code_search = wait.until(
                    EC.presence_of_element_located((By.ID, "Postcode"))
                )
                print(f"Found postcode input field, entering postcode: {postcode}")
                post_code_search.send_keys(postcode)
                # Add a small delay after entering the postcode
                time.sleep(1)
            except Exception as e:
                print(f"Error finding or interacting with postcode field: {e}")
                print(f"Page title: {driver.title}")
                print(f"Page source length: {len(driver.page_source)}")
                raise

            # Click the Find address button
            print("Looking for 'Find address' button...")
            try:
                submit_btn = wait.until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "//input[@type='submit' and @class='button button--secondary']",
                        )
                    )
                )
                print("Found 'Find address' button, scrolling to it...")
                # Scroll the button into view
                driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
                time.sleep(1)

                # Use Keys.ENTER as requested
                print("Clicking button using Keys.ENTER...")
                submit_btn.send_keys(Keys.ENTER)

                # Add a delay after clicking the button
                time.sleep(3)
            except Exception as e:
                print(f"Error finding or clicking 'Find address' button: {e}")
                print(f"Page title: {driver.title}")
                print(f"Page source length: {len(driver.page_source)}")
                raise

            # Wait for the address dropdown to appear
            print("Waiting for address dropdown to appear...")
            try:
                address_dropdown = wait.until(
                    EC.presence_of_element_located((By.ID, "UprnAddress"))
                )
                print("Found address dropdown")
                # Add a delay after finding the dropdown
                time.sleep(2)
            except Exception as e:
                print(f"Error finding address dropdown: {e}")
                print(f"Page title: {driver.title}")
                print(f"Page source length: {len(driver.page_source)}")
                raise

            # Create a Select object for the dropdown
            dropdown_select = Select(address_dropdown)

            # Search for the exact address as defined in the JSON
            print(f"Looking for address: {user_paon}")

            try:
                # Select the address by visible text
                dropdown_select.select_by_visible_text(user_paon)
                print(f"Selected address: {user_paon}")
            except Exception as e:
                print(f"Error selecting address by visible text: {e}")
                # If we can't find the exact address, raise an error
                raise ValueError(f"Could not find address '{user_paon}' in dropdown")

            # Add a delay after selecting the address
            time.sleep(2)

            # Click the confirm selection button
            print("Looking for 'Confirm selection' button...")
            try:
                next_btn = wait.until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "//input[@type='submit' and @class='button button--primary' and @value='Confirm selection']",
                        )
                    )
                )
                print("Found 'Confirm selection' button, scrolling to it")
                driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                time.sleep(1)
            except Exception as e:
                print(f"Error finding 'Confirm selection' button: {e}")
                print(f"Page title: {driver.title}")
                print(f"Page source length: {len(driver.page_source)}")
                raise

            # Use Keys.ENTER as requested
            try:
                print("Clicking button using Keys.ENTER")
                next_btn.send_keys(Keys.ENTER)
                # Add a delay after clicking the button
                time.sleep(3)
            except Exception as e:
                print(f"Keys.ENTER click failed: {e}")
                try:
                    # Try regular click as fallback
                    print("Trying regular click")
                    next_btn.click()
                    time.sleep(3)
                except Exception as e2:
                    print(f"Regular click failed: {e2}")
                    # Try one more approach - find by different selector
                    try:
                        print("Trying to find button by different selector")
                        confirm_btn = driver.find_element(
                            By.CSS_SELECTOR, "input.button.button--primary"
                        )
                        confirm_btn.send_keys(Keys.ENTER)
                        time.sleep(3)
                    except Exception as e3:
                        print(f"Alternative selector failed: {e3}")
                        raise

            # Wait for collection details to be present in the page
            print("Waiting for collection details to appear...")
            try:
                wait.until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "//div[contains(@class, 'card-body')]//h4[contains(text(), 'Your next collections')]",
                        )
                    )
                )
                print("Found collection details")
            except Exception as e:
                print(f"Error waiting for collection details: {e}")
                print(f"Page title: {driver.title}")
                print(f"Page source length: {len(driver.page_source)}")
                print("Page source preview:")
                print(driver.page_source[:1000])

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

                    if not bin_divs:
                        # If we can't find them as siblings, look within the card-body
                        bin_divs = card_body.find_all("div", class_="my-2")

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
                                    dict_data = {
                                        "type": bin_type,
                                        "collectionDate": bin_date,
                                    }
                                    data["bins"].append(dict_data)
                                    print(f"Added bin data: {dict_data}")

            # If we still don't have any bin data, try a more generic approach
            if not data["bins"]:
                print(
                    "No bin data found with specific selectors, trying alternative approach"
                )

                # Look for all strong tags that might contain bin types
                strong_tags = soup.find_all("strong")
                for strong_tag in strong_tags:
                    bin_type = strong_tag.text.strip()

                    # Skip if not a likely bin type
                    if not any(
                        bin_word in bin_type.lower()
                        for bin_word in [
                            "food",
                            "rubbish",
                            "recycling",
                            "garden",
                            "waste",
                            "bin",
                        ]
                    ):
                        continue

                    # Get the parent element
                    parent = strong_tag.parent
                    if parent:
                        # Get the text after the bin type
                        full_text = parent.get_text(strip=True)
                        date_text = full_text.replace(bin_type, "").strip()

                        # Parse the date
                        bin_date = self._parse_date(date_text)

                        if bin_type and bin_date:
                            dict_data = {"type": bin_type, "collectionDate": bin_date}
                            data["bins"].append(dict_data)
                            print(f"Added bin data: {dict_data}")

                # If we still don't have data, dump the HTML structure for debugging
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
