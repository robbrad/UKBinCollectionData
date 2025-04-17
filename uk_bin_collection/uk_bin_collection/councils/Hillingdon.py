from datetime import datetime, timedelta
import json
from typing import Dict, Any

from bs4 import BeautifulSoup
from dateutil.parser import parse
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# Dictionary mapping day names to their weekday numbers (Monday=0, Sunday=6)
DAYS_OF_WEEK = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}

# This function checks for bank holiday collection changes, 
# but the page seems manually written so might break easily
def get_bank_holiday_changes(driver: WebDriver) -> Dict[str, str]:
    """Fetch and parse bank holiday collection changes from the council website."""
    bank_holiday_url = "https://www.hillingdon.gov.uk/bank-holiday-collections"
    driver.get(bank_holiday_url)
    
    # Wait for page to load
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    
    # Parse the page
    soup = BeautifulSoup(driver.page_source, features="html.parser")
    changes: Dict[str, str] = {}
    
    # Find all tables with collection changes
    tables = soup.find_all("table")
    for table in tables:
        # Check if this is a collection changes table
        headers = [th.text.strip() for th in table.find_all("th")]
        if "Normal collection day" in headers and "Revised collection day" in headers:
            # Process each row
            for row in table.find_all("tr")[1:]:  # Skip header row
                cols = row.find_all("td")
                if len(cols) >= 2:
                    normal_date = cols[0].text.strip()
                    revised_date = cols[1].text.strip()
                    
                    # Parse dates
                    try:
                        normal_date = parse(normal_date, fuzzy=True).strftime("%d/%m/%Y")
                        revised_date = parse(revised_date, fuzzy=True).strftime("%d/%m/%Y")
                        changes[normal_date] = revised_date
                    except Exception as e:
                        print(f"Error parsing dates: {e}")
                        continue
    
    return changes

class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs: Any) -> Dict[str, Any]:
        driver = None
        try:
            data: Dict[str, Any] = {"bins": []}
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            url = kwargs.get("url")

            check_paon(user_paon)
            check_postcode(user_postcode)

            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(url)
            
            # Handle cookie banner if present
            wait = WebDriverWait(driver, 10)
            try:
                cookie_button = wait.until(
                    EC.element_to_be_clickable(
                        (By.CLASS_NAME, "btn btn--cookiemessage btn--cancel btn--contrast")
                    )
                )
                cookie_button.click()
            except (TimeoutException, NoSuchElementException):
                pass

            # Enter postcode
            post_code_input = wait.until(
                EC.element_to_be_clickable((By.ID, "WASTECOLLECTIONDAYLOOKUPINCLUDEGARDEN_ADDRESSLOOKUPPOSTCODE"))
            )
            post_code_input.clear()
            post_code_input.send_keys(user_postcode)
            post_code_input.send_keys(Keys.TAB + Keys.ENTER)

            # Wait for address options to populate
            try:
                # Wait for the address dropdown to be present and clickable
                address_select = wait.until(
                    EC.presence_of_element_located((By.ID, "WASTECOLLECTIONDAYLOOKUPINCLUDEGARDEN_ADDRESSLOOKUPADDRESS"))
                )
                
                # Wait for actual address options to appear
                wait.until(lambda driver: len(driver.find_elements(By.TAG_NAME, "option")) > 1)
                
                # Find and select address
                options = address_select.find_elements(By.TAG_NAME, "option")[1:]  # Skip placeholder
                if not options:
                    raise Exception(f"No addresses found for postcode: {user_postcode}")
                
                # Normalize user input by keeping only alphanumeric characters
                normalized_user_input = "".join(c for c in user_paon if c.isalnum()).lower()
                
                # Find matching address in dropdown
                for option in options:
                    # Normalize option text by keeping only alphanumeric characters
                    normalized_option = "".join(c for c in option.text if c.isalnum()).lower()
                    if normalized_user_input in normalized_option:
                        option.click()
                        break
            except TimeoutException:
                raise Exception("Timeout waiting for address options to populate")

            # Wait for collection table and day text
            wait.until(
                EC.presence_of_element_located((By.ID, "WASTECOLLECTIONDAYLOOKUPINCLUDEGARDEN_COLLECTIONTABLE"))
            )
            
            # Wait for collection day text to be fully populated
            wait.until(
                lambda driver: len(
                    driver.find_element(By.ID, "WASTECOLLECTIONDAYLOOKUPINCLUDEGARDEN_COLLECTIONTABLE")
                    .find_elements(By.TAG_NAME, "tr")[2]
                    .find_elements(By.TAG_NAME, "td")[1]
                    .text.strip()
                    .split()
                ) > 1
            )

            # Parse the table
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            table = soup.find("div", id="WASTECOLLECTIONDAYLOOKUPINCLUDEGARDEN_COLLECTIONTABLE").find("table")
            
            # Get collection day
            collection_day_text = table.find_all("tr")[2].find_all("td")[1].text.strip()
            day_of_week = next((day for day in DAYS_OF_WEEK if day.lower() in collection_day_text.lower()), None)
            if not day_of_week:
                raise Exception(f"Could not determine collection day from text: '{collection_day_text}'")
            
            # Calculate next collection date
            today = datetime.now()
            days_ahead = (DAYS_OF_WEEK[day_of_week] - today.weekday()) % 7
            if days_ahead == 0:  # If today is collection day, get next week's date
                days_ahead = 7
            next_collection = today + timedelta(days=days_ahead)
            
            # Add collection dates for each bin type
            bin_types = ["General Waste", "Recycling", "Food Waste"]
            for bin_type in bin_types:
                data["bins"].append({
                    "type": bin_type,
                    "collectionDate": next_collection.strftime("%d/%m/%Y"),
                })

            # Process collection details
            bin_rows = soup.select("div.bin--row:not(:first-child)")
            for row in bin_rows:
                try:
                    bin_type = row.select_one("div.col-md-3").text.strip()
                    collection_dates_div = row.select("div.col-md-3")[1]
                    next_collection_text = "".join(
                        collection_dates_div.find_all(text=True, recursive=False)
                    ).strip()
                    cleaned_date_text = remove_ordinal_indicator_from_date_string(next_collection_text)
                    parsed_date = parse(cleaned_date_text, fuzzy=True)
                    bin_date = parsed_date.strftime("%d/%m/%Y")

                    if bin_type and bin_date:
                        data["bins"].append({
                            "type": bin_type,
                            "collectionDate": bin_date,
                        })
                except Exception as e:
                    print(f"Error processing item: {e}")
                    continue

            # Get bank holiday changes
            print("\nChecking for bank holiday collection changes...")
            bank_holiday_changes = get_bank_holiday_changes(driver)
            
            # Apply any bank holiday changes to collection dates
            for bin_data in data["bins"]:
                original_date = bin_data["collectionDate"]
                if original_date in bank_holiday_changes:
                    new_date = bank_holiday_changes[original_date]
                    print(f"Bank holiday change: {bin_data['type']} collection moved from {original_date} to {new_date}")
                    bin_data["collectionDate"] = new_date

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()

        # Print the final data dictionary for debugging
        print("\nFinal data dictionary:")
        print(json.dumps(data, indent=2))

        return data

