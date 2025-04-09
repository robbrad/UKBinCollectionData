# This script pulls (in one hit) the data from Broadland District Council Bins Data
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
            user_paon = kwargs.get("paon")
            postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

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
                print("Found 'Find address' button, clicking it...")
                submit_btn.click()
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

            # Simplified approach: Try to find the address directly by partial text match
            print(f"Looking for address containing: {user_paon}")

            # Get the first part of the address (usually the house number)
            house_number = user_paon.split()[0]
            print(f"House number to match: {house_number}")

            # Try to find an option with the house number
            try:
                # First, try to find by the full address
                for i, option in enumerate(dropdown_select.options):
                    if i == 0:  # Skip the first option which is usually a placeholder
                        continue

                    if user_paon in option.text:
                        print(f"Found matching address: {option.text}")
                        dropdown_select.select_by_index(i)
                        break
                else:
                    # If not found, try to find by house number
                    for i, option in enumerate(dropdown_select.options):
                        if i == 0:  # Skip the first option
                            continue

                        if option.text.startswith(house_number):
                            print(f"Found address by house number: {option.text}")
                            dropdown_select.select_by_index(i)
                            break
                    else:
                        # If still not found, just select the first non-placeholder option
                        print("No exact match found, selecting the first valid option")
                        if len(dropdown_select.options) > 1:
                            dropdown_select.select_by_index(1)
                        else:
                            raise ValueError("No valid addresses found in dropdown")
            except Exception as e:
                print(f"Error selecting address: {e}")
                # Try a different approach if the above fails
                try:
                    # Try using JavaScript to select the option
                    print("Trying to select address using JavaScript")
                    for i, option in enumerate(dropdown_select.options):
                        if i == 0:  # Skip the first option
                            continue

                        if user_paon in option.text or option.text.startswith(
                            house_number
                        ):
                            driver.execute_script(
                                f"document.getElementById('UprnAddress').selectedIndex = {i};"
                            )
                            driver.execute_script(
                                "document.getElementById('UprnAddress').dispatchEvent(new Event('change'));"
                            )
                            print(f"Selected address using JavaScript: {option.text}")
                            break
                    else:
                        # If still not found, select the first non-placeholder option
                        if len(dropdown_select.options) > 1:
                            driver.execute_script(
                                "document.getElementById('UprnAddress').selectedIndex = 1;"
                            )
                            driver.execute_script(
                                "document.getElementById('UprnAddress').dispatchEvent(new Event('change'));"
                            )
                        else:
                            raise ValueError("No valid addresses found in dropdown")
                except Exception as e2:
                    print(f"JavaScript selection failed: {e2}")
                    raise

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

            # Try to click using JavaScript
            try:
                print("Clicking button using JavaScript")
                driver.execute_script("arguments[0].click();", next_btn)
                # Add a delay after clicking the button
                time.sleep(3)
            except Exception as e:
                print(f"JavaScript click failed: {e}")
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
                        driver.execute_script("arguments[0].click();", confirm_btn)
                        time.sleep(3)
                    except Exception as e3:
                        print(f"Alternative selector failed: {e3}")
                        raise

            # Wait for collection details to be present in the page
            print("Waiting for collection details to appear...")
            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(@class, 'collection-details')]")
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
            collection_details = soup.find_all(class_="collection-details")

            if not collection_details:
                collection_details = soup.find_all(class_="collection-type")

            for collection in collection_details:
                bin_type_elem = collection.find(class_="collection-type")
                bin_type = bin_type_elem.text.strip() if bin_type_elem else "Unknown"

                date_elem = collection.find(class_="collection-date")
                bin_date = None
                if date_elem:
                    date_text = date_elem.text.strip()
                    bin_date = self._parse_date(date_text)

                if bin_type and bin_date:
                    dict_data = {"type": bin_type, "collectionDate": bin_date}
                    data["bins"].append(dict_data)

            # If we still don't have any bin data, try a more generic approach
            if not data["bins"]:
                print(
                    "No bin data found with specific selectors, trying generic text extraction"
                )
                bin_types = [
                    "Recycling",
                    "General Waste",
                    "Food Waste",
                    "Garden Waste",
                    "Black Bin",
                    "Green Bin",
                    "Brown Bin",
                    "Blue Bin",
                ]

                for bin_type in bin_types:
                    elements = soup.find_all(
                        string=lambda text: bin_type in text if text else False
                    )
                    for element in elements:
                        print(f"Found element containing '{bin_type}': {element}")
                        parent = element.parent
                        if parent:
                            siblings = list(parent.next_siblings) + list(
                                parent.previous_siblings
                            )
                            for sibling in siblings:
                                if hasattr(sibling, "text"):
                                    date_pattern = r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
                                    date_match = re.search(date_pattern, sibling.text)
                                    if date_match:
                                        bin_date = self._parse_date(sibling.text)
                                        if bin_date:
                                            dict_data = {
                                                "type": bin_type,
                                                "collectionDate": bin_date,
                                            }
                                            data["bins"].append(dict_data)
                                            print(f"Added bin data: {dict_data}")
                                            break

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            print("Cleaning up webdriver...")
            if driver:
                driver.quit()

        return data

    def _parse_date(self, date_text):
        """Helper method to parse dates in various formats"""
        bin_date = None
        try:
            # Try common date formats
            date_formats = [
                "%d %B %Y",
                "%d %b %Y",
                "%A %d %B %Y",
                "%A %d %b %Y",
            ]
            for fmt in date_formats:
                try:
                    bin_date = datetime.strptime(date_text, fmt)
                    bin_date = bin_date.strftime("%d/%m/%Y")
                    break
                except ValueError:
                    continue
        except Exception:
            pass

        # If we couldn't parse the date, try to extract it with regex
        if not bin_date:
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
