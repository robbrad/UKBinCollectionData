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

            # Create BS4 object from driver's page source
            # print("Parsing page with BeautifulSoup...")
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Initialize data dictionary
            data = {"bins": []}

            for row in soup.select(".listing_template_row"):
                # Title (waste stream) is the first <p> in the section
                first_p = row.find("p")
                if not first_p:
                    continue
                stream = first_p.get_text(" ", strip=True)

                for p in row.find_all("p"):
                    t = p.get_text("\n", strip=True)

                    if re.search(r"\bNext collection\b", t, flags=re.I):
                        # Expect format: "Next collection\nTuesday 16th September 2025"
                        parts = [x.strip() for x in t.split("\n") if x.strip()]
                        if len(parts) >= 2:
                            next_collection_display = parts[-1]  # last line

                # Build record
                next_date = datetime.strptime(
                    remove_ordinal_indicator_from_date_string(next_collection_display),
                    "%A %d %B %Y",
                )

                # Create bin entry
                bin_entry = {
                    "type": stream,
                    "collectionDate": next_date.strftime(date_format),
                }

                # Add to data
                data["bins"].append(bin_entry)
                # print(f"Added bin entry: {bin_entry}")

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
