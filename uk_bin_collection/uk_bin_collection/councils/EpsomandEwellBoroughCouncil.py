import re
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        driver = None
        try:
            driver = create_webdriver(
                kwargs.get("web_driver"),
                kwargs.get("headless", True),
                None,
                __name__
            )
            
            # Navigate to the iTouchVision portal
            portal_url = "https://iportal.itouchvision.com/icollectionday/collection-day/?uuid=8E7DCC4BD90D8405D154BE053147018A8C0B5F09"
            driver.get(portal_url)
            
            # Wait for postcode input to be present
            postcode_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "postcodeSearch"))
            )
            
            # Enter postcode using JavaScript to trigger React events
            if user_postcode:
                postcode = user_postcode
            else:
                # If no postcode provided, we need to derive it from UPRN
                # For now, raise an error
                raise ValueError("Postcode is required for EpsomandEwellBoroughCouncil")
            
            driver.execute_script(f"""
                const input = document.getElementById('postcodeSearch');
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(input, '{postcode}');
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            """)
            
            # Click the Find button
            find_button = driver.find_element(By.CSS_SELECTOR, ".govuk-button")
            find_button.click()
            
            # Wait for address dropdown to appear and be populated
            address_select = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "addressSelect"))
            )
            
            # Wait a bit for options to populate
            import time
            time.sleep(2)
            
            # Select the address by UPRN value using JavaScript
            driver.execute_script(f"""
                const select = document.getElementById('addressSelect');
                select.value = '{user_uprn}';
                select.dispatchEvent(new Event('change', {{ bubbles: true }}));
            """)
            
            # Wait for collection data to load (look for h3 elements with bin types)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h3"))
            )
            
            # Wait a bit more for all data to render
            time.sleep(3)
            
            # Get the page source and parse with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Find all h3 elements (these contain bin types)
            h3_elements = soup.find_all("h3")
            
            for h3 in h3_elements:
                bin_type = h3.text.strip()
                
                # Skip if empty
                if not bin_type:
                    continue
                
                # Get the next sibling element which should contain the date
                next_elem = h3.find_next_sibling()
                if not next_elem:
                    continue
                
                date_text = next_elem.text.strip()
                
                # Parse date in format "Thursday 11 December"
                # Need to add current year
                try:
                    # Extract day and month from "Thursday 11 December" format
                    match = re.search(r'(\w+)\s+(\d{1,2})\s+(\w+)', date_text)
                    if match:
                        day = match.group(2)
                        month = match.group(3)
                        
                        # Determine the year (if month is in the past, use next year)
                        current_date = datetime.now()
                        current_year = current_date.year
                        
                        # Try parsing with current year
                        try:
                            date_obj = datetime.strptime(f"{day} {month} {current_year}", "%d %B %Y")
                            # If the date is more than 30 days in the past, assume it's next year
                            if (current_date - date_obj).days > 30:
                                date_obj = datetime.strptime(f"{day} {month} {current_year + 1}", "%d %B %Y")
                        except ValueError:
                            # Try with next year
                            date_obj = datetime.strptime(f"{day} {month} {current_year + 1}", "%d %B %Y")
                        
                        collection_date = date_obj.strftime(date_format)
                        
                        dict_data = {
                            "type": bin_type,
                            "collectionDate": collection_date,
                        }
                        bindata["bins"].append(dict_data)
                except Exception as e:
                    print(f"Error parsing date '{date_text}': {e}")
                    continue
            
            # Sort by collection date
            bindata["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
            )
            
        finally:
            if driver:
                driver.quit()

        return bindata
