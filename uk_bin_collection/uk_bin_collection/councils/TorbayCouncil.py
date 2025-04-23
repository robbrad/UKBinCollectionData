# This script pulls bin collection data from Barking and Dagenham Council
# Example URL: https://www.lbbd.gov.uk/rubbish-recycling/household-bin-collection/check-your-bin-collection-days
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

            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            url = kwargs.get("url")

            check_postcode(user_postcode)

            print(
                f"Starting parse_data with parameters: postcode={user_postcode}, uprn={user_uprn}"
            )
            print(
                f"Creating webdriver with: web_driver={web_driver}, headless={headless}"
            )

            driver = create_webdriver(web_driver, headless, None, __name__)
            print(f"Navigating to URL: {url}")
            driver.get(url)
            print("Successfully loaded the page")

            driver.maximize_window()

            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Handle cookie banner if present
            wait = WebDriverWait(driver, 60)
            try:
                cookie_button = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "/html/body/div[1]/div/div[2]/button[1]",
                        )
                    ),
                    message="Cookie banner not found",
                )
                cookie_button.click()
                print("Cookie banner clicked.")
                time.sleep(1)  # Brief pause to let banner disappear
            except (TimeoutException, NoSuchElementException):
                print("No cookie banner appeared or selector failed.")

            bin_collection_button = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "/html/body/main/div[4]/div/div[1]/div/div/div/div/div[2]/div/div/div/p/a",
                    )
                ),
            )
            bin_collection_button.click()

            # Save the original window
            original_window = driver.current_window_handle

            # Wait for the new window or tab
            WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

            # Loop through until we find a new window handle
            for window_handle in driver.window_handles:
                if window_handle != original_window:
                    driver.switch_to.window(window_handle)
                    break
            # Now you're in the new tab and can interact with the postcode input
            # Enter postcode
            print("Looking for postcode input...")
            wait.until(EC.presence_of_element_located((By.ID, "FF1168-text")))
            post_code_input = wait.until(
                EC.element_to_be_clickable((By.ID, "FF1168-text")),
                message="Postcode input not clickable",
            )
            post_code_input.clear()
            post_code_input.send_keys(user_postcode)
            print(f"Entered postcode: {user_postcode}")

            post_code_input.send_keys(Keys.TAB + Keys.ENTER)
            # driver.switch_to.active_element.send_keys(Keys.TAB + Keys.ENTER)
            print("Pressed ENTER on Search button")

            # Wait for the dropdown to be clickable
            address_select = wait.until(
                EC.element_to_be_clickable((By.ID, "FF1168-list")),
                message="Address dropdown not found",
            )

            # Click to focus the dropdown
            address_select.click()
            time.sleep(0.5)  # Brief pause to let the dropdown open

            # Get all options
            options = address_select.find_elements(By.TAG_NAME, "option")
            print(f"Found {len(options)} options in dropdown")

            # Print all options first for debugging
            print("\nAvailable options:")
            for opt in options:
                value = opt.get_attribute("value")
                text = opt.text
                print(f"Value: '{value}', Text: '{text}'")

            # Try to find our specific UPRN
            target_uprn = f"U{user_uprn}|"
            print(f"\nLooking for UPRN pattern: {target_uprn}")

            found = False
            for option in options:
                value = option.get_attribute("value")
                if value and target_uprn in value:
                    print(f"Found matching address with value: {value}")
                    option.click()
                    found = True
                    break

            if not found:
                print(f"No matching address found for UPRN: {user_uprn}")
                return data

            print("Address selected successfully")
            time.sleep(1)  # Give time for the selection to take effect

            # Find and click the Submit button
            submit_button = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.btn.btn-primary[type='submit']")
                ),
                message="Submit button not found or not clickable",
            )
            submit_button.click()
            time.sleep(1)  # Give time for the submission to process

            print("Clicked Submit button")

            print("Looking for schedule list...")
            schedule_list = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "bin--container"))
            )

            # Make a BS4 object
            print("Parsing page with BeautifulSoup...")
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Process collection details
            print("Looking for collection details in the page...")

            bin_rows = soup.select("div.bin--row:not(:first-child)")  # Skip header row
            print(f"\nProcessing {len(bin_rows)} bin rows...")

            for row in bin_rows:
                try:
                    # Extract bin type from first column
                    bin_type = row.select_one("div.col-md-3").text.strip()

                    # Get the collection dates column
                    collection_dates_div = row.select("div.col-md-3")[1]  # Third column

                    # Get only the immediate text content before any <p> tags
                    next_collection_text = "".join(
                        collection_dates_div.find_all(text=True, recursive=False)
                    ).strip()

                    # Parse the date
                    cleaned_date_text = remove_ordinal_indicator_from_date_string(
                        next_collection_text
                    )
                    parsed_date = parse(cleaned_date_text, fuzzy=True)
                    bin_date = parsed_date.strftime("%d/%m/%Y")

                    # Add to data
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
