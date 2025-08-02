import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

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
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            
            # Navigate to the start page
            driver.get("https://chorley.gov.uk/bincollectiondays")
            
            # Click the "Check your collection day" button
            check_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@class='button' and @href='https://forms.chorleysouthribble.gov.uk/chorley-bincollectiondays']")
            ))
            check_button.click()
            
            # Wait for the form to load and enter postcode
            postcode_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='text'][1]")
            ))
            postcode_input.clear()
            postcode_input.send_keys(user_postcode)
            
            # Click the Lookup button
            lookup_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn--lookup')]")
            ))
            lookup_button.click()
            
            # Wait for the property dropdown to be populated
            property_dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//select[@class='form__select']")
            ))
            
            # Wait a moment for the dropdown to be fully populated
            time.sleep(2)
            
            # Find the property that matches the UPRN or select the first available property
            select = Select(property_dropdown)
            options = select.options
            
            # Skip the "Please choose..." option and select based on UPRN or first available
            selected = False
            for option in options[1:]:  # Skip first "Please choose..." option
                if user_uprn in option.get_attribute("value") or not selected:
                    select.select_by_visible_text(option.text)
                    selected = True
                    break
            
            if not selected and len(options) > 1:
                # If no UPRN match, select the first available property
                select.select_by_index(1)
            
            # Click the Next button
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'][value='Next']"))
            )
            next_button.click()
            
            # Wait for the results page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//th[text()='Collection']"))
            )
            
            # Parse the results
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Find the table with collection data
            table = soup.find("table")
            
            if table:
                rows = table.find_all("tr")
                
                for i, row in enumerate(rows):
                    cells = row.find_all(["td", "th"])
                    
                    if i > 0 and len(cells) >= 2:  # Skip header row
                        collection_type = cells[0].get_text(strip=True)
                        collection_date = cells[1].get_text(strip=True)
                        
                        if collection_type and collection_date and collection_date != "Collection":
                            # Try to parse the date
                            try:
                                # Handle the format "Tuesday, 05/08/25"
                                if ", " in collection_date and "/" in collection_date:
                                    # Remove the day name and parse the date
                                    date_part = collection_date.split(", ")[1]
                                    # Handle 2-digit year format
                                    if len(date_part.split("/")[2]) == 2:
                                        date_obj = datetime.strptime(date_part, "%d/%m/%y")
                                    else:
                                        date_obj = datetime.strptime(date_part, "%d/%m/%Y")
                                elif "/" in collection_date:
                                    date_obj = datetime.strptime(collection_date, "%d/%m/%Y")
                                elif "-" in collection_date:
                                    date_obj = datetime.strptime(collection_date, "%Y-%m-%d")
                                else:
                                    # Try to parse other formats
                                    date_obj = datetime.strptime(collection_date, "%d %B %Y")
                                
                                formatted_date = date_obj.strftime("%d/%m/%Y")
                                
                                dict_data = {
                                    "type": collection_type,
                                    "collectionDate": formatted_date,
                                }
                                data["bins"].append(dict_data)
                            except ValueError:
                                # If date parsing fails, skip this entry
                                continue
            
        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            if driver:
                driver.quit()
        return data