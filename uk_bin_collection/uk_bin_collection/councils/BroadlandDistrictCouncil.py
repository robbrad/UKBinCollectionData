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
            try:
                # Adjust the selector depending on the site's button
                accept_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
                    )
                )
                accept_button.click()
                print("Cookie banner clicked.")
            except:
                print("No cookie banner appeared or selector failed.")

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
                        bin_type = None

                        if bin_type_elem:
                            bin_type = bin_type_elem.text.strip().replace(
                                " (if applicable)", ""
                            )

                            # Get the parent element that contains both the bin type and date
                            text_container = bin_type_elem.parent
                            if text_container:
                                # Extract the full text and remove the bin type to get the date part
                                full_text = text_container.get_text(strip=True)
                                date_text = full_text.replace(bin_type, "").strip()
                                print(f"Unparsed collection date: {date_text}")

                                # Parse the date
                                # First, remove any ordinal indicators (1st, 2nd, 3rd, etc.)
                                cleaned_date_text = (
                                    remove_ordinal_indicator_from_date_string(date_text)
                                )

                                from dateutil.parser import parse

                                parsed_date = parse(cleaned_date_text, fuzzy=True)
                                bin_date = parsed_date.strftime("%d/%m/%Y")

                                # Only process if we have both bin_type and bin_date
                                if bin_type and bin_date:
                                    dict_data = {
                                        "type": bin_type,
                                        "collectionDate": bin_date,
                                    }
                                    data["bins"].append(dict_data)
                                    print(f"Added bin data: {dict_data}")
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            print("Cleaning up webdriver...")
            if driver:
                driver.quit()

        return data
