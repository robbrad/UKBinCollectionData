# direct URL works, but includes a token, so I'm using Selenium
# https://waste.nc.north-herts.gov.uk/w/webpage/find-bin-collection-day-show-details?webpage_token=c7c7c3cbc2f0478735fc746ca985b8f4221dea31c24dde99e39fb1c556b07788&auth=YTc5YTAwZmUyMGQ3&id=1421457

import re
import time
from datetime import datetime

from bs4 import BeautifulSoup
from dateutil.parser import parse
from selenium.common.exceptions import NoSuchElementException, TimeoutException
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

            user_paon = kwargs.get("paon")
            postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            url = "https://waste.nc.north-herts.gov.uk/w/webpage/find-bin-collection-day-input-address"

            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(url)

            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Define the wait variable
            wait = WebDriverWait(
                driver, 20
            )  # Create the wait object with a 20-second timeout

            # Enter postcode - try different approaches for reliability
            # print("Looking for postcode input...")

            postcode_input = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "input.relation_path_type_ahead_search.form-control",
                    )
                ),
                message="Postcode input not found by class",
            )
            postcode_input.clear()
            postcode_input.send_keys(postcode)
            # print(f"Entered postcode: {postcode}")

            # Wait for the dropdown to load
            # print("Waiting for address list to populate...")
            try:
                # Wait for the results to appear
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".relation_path_type_ahead_results_holder")
                    ),
                    message="Address results container not found",
                )

                # Wait for list items to appear
                wait.until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, ".relation_path_type_ahead_results_holder li")
                    ),
                    message="No address items found in the list",
                )
                # print("Address list populated successfully")

                # Search for user_paon in the address list using aria-label attribute
                try:
                    # Use XPath to look for aria-label containing user_paon
                    address_xpath = (
                        f"//li[@aria-label and contains(@aria-label, '{user_paon}')]"
                    )
                    matching_address = wait.until(
                        EC.element_to_be_clickable((By.XPATH, address_xpath)),
                        message=f"No address containing '{user_paon}' found in aria-label attributes",
                    )
                    # print(f"Found matching address: {matching_address.get_attribute('aria-label')}")
                    matching_address.click()
                    # print("Clicked on matching address")

                    # Allow time for the selection to take effect
                    time.sleep(2)

                    # Find and click the "Select address and continue" button
                    continue_button = wait.until(
                        EC.element_to_be_clickable(
                            (
                                By.CSS_SELECTOR,
                                "input.btn.bg-green[value='Select address and continue']",
                            )
                        ),
                        message="Could not find 'Select address and continue' button",
                    )
                    # print("Found 'Select address and continue' button, clicking it...")
                    continue_button.click()
                    # print("Clicked on 'Select address and continue' button")

                    # Allow time for the page to load after clicking the button
                    time.sleep(3)
                except TimeoutException as e:
                    # print(f"Error finding address: {e}")
                    raise
            except TimeoutException as e:
                # print(f"Error loading address list: {e}")
                raise

            # After pressing Next button and waiting for page to load
            # print("Looking for schedule list...")

            # Wait for the page to load - giving it extra time
            time.sleep(5)

            # Use only the selector that we know works
            # print("Looking for bin type elements...")
            try:
                bin_type_selector = (
                    By.CSS_SELECTOR,
                    "div.formatting_bold.formatting_size_bigger.formatting span.value-as-text",
                )
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located(bin_type_selector)
                )
                # print(f"Found bin type elements with selector: {bin_type_selector}")
            except TimeoutException:
                # print("Could not find bin type elements. Taking screenshot for debugging...")
                screenshot_path = f"bin_type_error_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                # print(f"Screenshot saved to {screenshot_path}")

            # Create BS4 object from driver's page source
            # print("Parsing page with BeautifulSoup...")
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Initialize data dictionary
            data = {"bins": []}

            # Looking for bin types in the exact HTML structure
            bin_type_elements = soup.select(
                "div.formatting_bold.formatting_size_bigger.formatting span.value-as-text"
            )
            # print(f"Found {len(bin_type_elements)} bin type elements")

            # Look specifically for date elements with the exact structure
            date_elements = soup.select("div.col-sm-12.font-xs-3xl span.value-as-text")
            hidden_dates = soup.select(
                "div.col-sm-12.font-xs-3xl input[type='hidden'][value*='/']"
            )

            # print(f"Found {len(bin_type_elements)} bin types and {len(date_elements)} date elements")

            # We need a smarter way to match bin types with their dates
            bin_count = 0

            # Map of bin types to their collection dates
            bin_date_map = {}

            # Extract all date strings that look like actual dates
            date_texts = []
            date_pattern = re.compile(
                r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d+(?:st|nd|rd|th)?\s+\w+\s+\d{4}",
                re.IGNORECASE,
            )

            for element in date_elements:
                text = element.get_text(strip=True)
                if date_pattern.search(text):
                    date_texts.append(text)
                    # print(f"Found valid date text: {text}")

            # Find hidden date inputs with values in DD/MM/YYYY format
            hidden_date_values = []
            for hidden in hidden_dates:
                value = hidden.get("value", "")
                if re.match(r"\d{1,2}/\d{1,2}/\d{4}", value):
                    hidden_date_values.append(value)
                    # print(f"Found hidden date value: {value}")

            # When filtering date elements
            date_elements = soup.select("div.col-sm-12.font-xs-3xl span.value-as-text")
            valid_date_elements = []

            for element in date_elements:
                text = element.get_text(strip=True)
                if contains_date(text):
                    valid_date_elements.append(element)
                    # print(f"Found valid date element: {text}")
                else:
                    pass
                    # print(f"Skipping non-date element: {text}")

            # print(f"Found {len(bin_type_elements)} bin types and {len(valid_date_elements)} valid date elements")

            # When processing each bin type
            for i, bin_type_elem in enumerate(bin_type_elements):
                bin_type = bin_type_elem.get_text(strip=True)

                # Try to find a date for this bin type
                date_text = None

                # Look for a valid date element
                if i < len(valid_date_elements):
                    date_elem = valid_date_elements[i]
                    date_text = date_elem.get_text(strip=True)

                # If we don't have a valid date yet, try using the hidden input
                if not date_text or not contains_date(date_text):
                    if i < len(hidden_dates):
                        date_value = hidden_dates[i].get("value")
                        if contains_date(date_value):
                            date_text = date_value

                # Skip if we don't have a valid date
                if not date_text or not contains_date(date_text):
                    # print(f"No valid date found for bin type: {bin_type}")
                    continue

                # print(f"Found bin type: {bin_type} with date: {date_text}")

                try:
                    # Clean up the date text
                    date_text = remove_ordinal_indicator_from_date_string(date_text)

                    # Try to parse the date
                    try:
                        collection_date = datetime.strptime(
                            date_text, "%A %d %B %Y"
                        ).date()
                    except ValueError:
                        try:
                            collection_date = datetime.strptime(
                                date_text, "%d/%m/%Y"
                            ).date()
                        except ValueError:
                            # Last resort
                            collection_date = parse(date_text).date()

                    # Create bin entry
                    bin_entry = {
                        "type": bin_type,
                        "collectionDate": collection_date.strftime(date_format),
                    }

                    # Add to data
                    data["bins"].append(bin_entry)
                    bin_count += 1
                    # print(f"Added bin entry: {bin_entry}")

                except Exception as e:
                    pass
                    # print(f"Error parsing date '{date_text}': {str(e)}")

            # print(f"Successfully parsed {bin_count} bin collections")

            if not data["bins"]:
                # print("No bin data found. Saving page for debugging...")
                with open(f"debug_page_{int(time.time())}.html", "w") as f:
                    f.write(driver.page_source)
                driver.save_screenshot(f"final_error_screenshot_{int(time.time())}.png")
                raise ValueError(
                    "No bin collection data could be extracted from the page"
                )

            # Sort the bin collections by date
            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
            )

            return data

        except Exception as e:
            # print(f"Error parsing bin collection data: {e}")
            raise
