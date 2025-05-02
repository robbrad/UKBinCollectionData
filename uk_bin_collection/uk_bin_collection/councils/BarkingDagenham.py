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

            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Close popup if it exists
            driver.switch_to.active_element.send_keys(Keys.ESCAPE)

            # Handle cookie banner if present
            wait = WebDriverWait(driver, 60)
            try:
                cookie_button = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            ".agree-button.eu-cookie-compliance-secondary-button.button.button--small",
                        )
                    ),
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
                EC.element_to_be_clickable((By.ID, "postcode")),
                message="Postcode input not found",
            )
            post_code_input.clear()
            post_code_input.send_keys(postcode)
            print(f"Entered postcode: {postcode}")

            driver.switch_to.active_element.send_keys(Keys.TAB + Keys.ENTER)
            print("Pressed ENTER on Search button")

            # Wait for and select address
            print("Waiting for address dropdown...")
            address_select = wait.until(
                EC.element_to_be_clickable((By.ID, "address")),
                message="Address dropdown not found",
            )
            
            dropdown = Select(address_select)

            found = False
            for option in dropdown.options:
                if user_paon in option.text:
                    option.click()
                    found = True
                    print("Address selected successfully")
                    break

            if not found:
                raise Exception(f"No matching address containing '{user_paon}' found.")

            driver.switch_to.active_element.send_keys(Keys.TAB + Keys.ENTER)
            print("Pressed ENTER on Next button")

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
