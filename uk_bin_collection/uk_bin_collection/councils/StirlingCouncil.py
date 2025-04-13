# This script pulls bin collection data from Stirling Council
# Example URL: https://www.stirling.gov.uk/bins-and-recycling/bin-collection-dates-search/
import time

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
            wait = WebDriverWait(driver, 60)

            # Handle cookie banner if present
            try:
                cookie_button = wait.until(
                    EC.element_to_be_clickable((By.ID, "ccc-recommended-settings")),
                    message="Cookie banner not found",
                )
                cookie_button.click()
                print("Cookie banner clicked.")
                time.sleep(1)  # Brief pause to let banner disappear
            except (TimeoutException, NoSuchElementException):
                print("No cookie banner appeared or selector failed.")

            # Enter postcode
            print("Looking for postcode input...")
            post_code_input = wait.until(
                EC.element_to_be_clickable((By.ID, "js-postcode-lookup-postcode")),
                message="Postcode input not found",
            )
            post_code_input.clear()
            post_code_input.send_keys(postcode)
            print(f"Entered postcode: {postcode}")

            driver.switch_to.active_element.send_keys(Keys.TAB + Keys.ENTER)
            print("Pressed ENTER on Find")

            # Wait for and select address
            print("Waiting for address dropdown...")
            address_select = wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "select__input")),
                message="Address dropdown not found",
            )
            dropdown = Select(address_select)

            dropdown.select_by_visible_text(user_paon)
            print("Address selected successfully")

            driver.switch_to.active_element.send_keys(Keys.TAB * 2 + Keys.ENTER)
            print("Pressed ENTER on Next button")

            print("Looking for schedule list...")
            schedule_list = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "schedule__list"))
            )

            # Make a BS4 object
            print("Parsing page with BeautifulSoup...")
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Process collection details
            print("Looking for collection details in the page...")

            schedule_items = []
            selectors = [
                "li.schedule__item",
            ]

            for selector in selectors:
                items = soup.select(selector)
                if items:
                    print(f"Found {len(items)} items using selector: {selector}")
                    schedule_items = items
                    break

            print(f"\nProcessing {len(schedule_items)} schedule items...")

            for item in schedule_items:
                try:
                    # Try multiple selectors for bin type
                    title = item.find("h2", class_="schedule__title")

                    bin_type = title.text.strip()

                    summary = item.find("p", class_="schedule__summary")

                    # Extract date text
                    summary_text = summary.get_text(strip=True)
                    print(f"Found summary text: {summary_text}")

                    # Try different date formats
                    date_text = None
                    for splitter in ["Then every", "then every", "Every"]:
                        if splitter in summary_text:
                            date_text = summary_text.split(splitter)[0].strip()
                            break

                    if not date_text:
                        date_text = summary_text  # Use full text if no splitter found

                    print(f"Extracted date text: {date_text}")

                    # Parse the date
                    cleaned_date_text = remove_ordinal_indicator_from_date_string(
                        date_text
                    )
                    parsed_date = parse(cleaned_date_text, fuzzy=True)
                    bin_date = parsed_date.strftime("%d/%m/%Y")

                    # Add only the next collection
                    if bin_type and bin_date:
                        dict_data = {
                            "type": bin_type,
                            "collectionDate": bin_date,
                        }
                        data["bins"].append(dict_data)
                        print(f"Successfully added collection: {dict_data}")

                except Exception as e:
                    print(f"Error processing item: {e}")
                    continue
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            print("Cleaning up webdriver...")
            if driver:
                driver.quit()

        return data
