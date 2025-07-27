from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
import re
import time

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
            check_uprn(user_uprn)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            
            # Navigate to the main page first
            driver.get("https://www.blaenau-gwent.gov.uk/en/resident/waste-recycling/")
            
            # Handle cookie overlay if present
            try:
                # Wait a moment for any overlays to appear
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.ID, "ccc-overlay"))
                )
                # Try to find and click cookie accept buttons
                cookie_buttons = [
                    "//button[contains(text(), 'Accept')]",
                    "//button[contains(text(), 'OK')]",
                    "//button[@id='ccc-recommended-settings']",
                    "//button[contains(@class, 'cookie')]"
                ]
                for button_xpath in cookie_buttons:
                    try:
                        cookie_button = driver.find_element(By.XPATH, button_xpath)
                        if cookie_button.is_displayed():
                            cookie_button.click()
                            break
                    except:
                        continue
            except:
                pass  # No cookie overlay found
            
            # Find and extract the collection day URL
            find_collection_link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Find Your Collection Day')]"))
            )
            collection_url = find_collection_link.get_attribute("href")
            
            # Navigate to the collection portal
            driver.get(collection_url)

            # Wait for the postcode field and enter postcode
            postcode_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "postcodeSearch"))
            )
            postcode_input.send_keys(user_postcode)

            # Click Find button
            find_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Find')]"))
            )
            find_button.click()

            # Wait for address dropdown and select by UPRN
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "addressSelect"))
            )
            dropdown = Select(driver.find_element(By.ID, "addressSelect"))
            dropdown.select_by_value(user_uprn)

            # Wait for collection data to load
            time.sleep(3)  # Give JavaScript time to process the selection
            
            # Wait for the actual collection data to appear
            WebDriverWait(driver, 20).until(
                lambda d: "Your next collections" in d.page_source and ("Recycling" in d.page_source or "Refuse" in d.page_source)
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            page_text = soup.get_text()
            
            # Find the collections section in the text
            if "Your next collections" in page_text:
                # Extract the section after "Your next collections"
                collections_section = page_text.split("Your next collections")[1]
                collections_section = collections_section.split("Related content")[0]  # Stop at Related content
                
                # Use regex to find collection patterns
                # Pattern to match: "Collection Type" followed by "Day Date Month" (stopping before 'followed')
                pattern = r'(Recycling collection|Refuse Bin)([A-Za-z]+ \d+ [A-Za-z]+)(?=followed|$|[A-Z])'
                matches = re.findall(pattern, collections_section)
                
                for bin_type, date_text in matches:
                    try:
                        # Clean up the date text
                        date_text = date_text.strip()
                        if "followed by" in date_text:
                            date_text = date_text.split("followed by")[0].strip()
                        
                        # Parse the date
                        collection_date = datetime.strptime(date_text, "%A %d %B")
                        
                        # Set the correct year
                        current_year = datetime.now().year
                        current_month = datetime.now().month
                        
                        if (current_month > 10) and (collection_date.month < 3):
                            collection_date = collection_date.replace(year=(current_year + 1))
                        else:
                            collection_date = collection_date.replace(year=current_year)

                        dict_data = {
                            "type": bin_type,
                            "collectionDate": collection_date.strftime("%d/%m/%Y"),
                        }
                        data["bins"].append(dict_data)
                    except ValueError:
                        pass  # Skip if date parsing fails

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        return data