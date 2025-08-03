import time
import re
from datetime import datetime, timedelta

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
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            page = "https://community.cotswold.gov.uk/s/waste-collection-enquiry"

            data = {"bins": []}

            house_number = kwargs.get("paon")
            postcode = kwargs.get("postcode")
            # Use house_number as full address since it contains the complete address
            full_address = house_number if house_number else f"{house_number}, {postcode}"
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            # Wait for page to load completely
            wait = WebDriverWait(driver, 60)
            
            # Wait for the Salesforce Lightning page to be fully loaded
            print("Waiting for Salesforce Lightning components to load...")
            time.sleep(10)
            
            # Wait for the address input field to be present
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'Enter your address')]")))
                print("Address label found")
                time.sleep(5)  # Additional wait for the input field to be ready
            except Exception as e:
                print(f"Address label not found: {e}")
            
            # Find the address input field using the label
            try:
                address_entry_field = driver.find_element(By.XPATH, "//label[contains(text(), 'Enter your address')]/following-sibling::*//input")
                print("Found address input field using label xpath")
            except Exception as e:
                print(f"Could not find address input field: {e}")
                raise Exception("Could not find address input field")
            
            # Clear any existing text and enter the address
            try:
                address_entry_field.clear()
                address_entry_field.send_keys(str(full_address))
                print(f"Entered address: {full_address}")
            except Exception as e:
                print(f"Error entering address: {e}")
                raise
            
            # Click the input field again to trigger the dropdown
            try:
                address_entry_field.click()
                print("Clicked input field to trigger dropdown")
                time.sleep(3)  # Wait for dropdown to appear
            except Exception as e:
                print(f"Error clicking input field: {e}")
            
            # Wait for and click the dropdown option
            try:
                dropdown_wait = WebDriverWait(driver, 10)
                dropdown_option = dropdown_wait.until(EC.element_to_be_clickable((By.XPATH, "//li[@role='presentation']")))
                dropdown_option.click()
                print("Clicked dropdown option")
                time.sleep(2)
            except Exception as e:
                print(f"Error clicking dropdown option: {e}")
                raise
            
            # Find and click the Next button
            try:
                next_wait = WebDriverWait(driver, 10)
                next_button = next_wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]")))
                next_button.click()
                print("Clicked Next button")
                time.sleep(5)  # Wait for the bin collection data to load
            except Exception as e:
                print(f"Error clicking Next button: {e}")
                raise
            
            # Wait for the bin collection data table to load
            try:
                table_wait = WebDriverWait(driver, 15)
                table_wait.until(EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Collection Day')]")))
                print("Bin collection data table loaded")
                time.sleep(3)
            except Exception as e:
                print(f"Bin collection table not found: {e}")
            
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            current_year = datetime.now().year

            # Try multiple approaches to find bin collection data
            rows = []
            
            # Try different table row selectors
            table_selectors = [
                "tr.slds-hint-parent",
                "tr[class*='slds']",
                "table tr",
                ".slds-table tr",
                "tbody tr"
            ]
            
            for selector in table_selectors:
                rows = soup.select(selector)
                if rows:
                    break
            
            # If no table rows found, try to find any elements containing collection info
            if not rows:
                # Look for any elements that might contain bin collection information
                collection_elements = soup.find_all(text=re.compile(r'(bin|collection|waste|recycling)', re.I))
                if collection_elements:
                    # Try to extract information from the surrounding elements
                    for element in collection_elements[:10]:  # Limit to first 10 matches
                        parent = element.parent
                        if parent:
                            text = parent.get_text().strip()
                            if text and len(text) > 10:  # Only consider substantial text
                                # Try to extract date patterns
                                date_patterns = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{1,2}\s+\w+\s+\d{4}\b', text)
                                if date_patterns:
                                    data["bins"].append({
                                        "type": "General Collection",
                                        "collectionDate": date_patterns[0]
                                    })
                                    break
            
            # Process table rows if found
            for row in rows:
                try:
                    columns = row.find_all(["td", "th"])
                    if len(columns) >= 2:
                        # Try to identify container type and date
                        container_type = "Unknown"
                        collection_date = ""
                        
                        # Look for header cell (th) for container type
                        th_element = row.find("th")
                        if th_element:
                            container_type = th_element.get_text().strip()
                        elif columns:
                            # If no th, use first column as type
                            container_type = columns[0].get_text().strip()
                        
                        # Look for date in subsequent columns
                        for col in columns[1:] if th_element else columns[1:]:
                            col_text = col.get_text().strip()
                            if col_text:
                                if col_text.lower() == "today":
                                    collection_date = datetime.now().strftime("%d/%m/%Y")
                                    break
                                elif col_text.lower() == "tomorrow":
                                    collection_date = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
                                    break
                                else:
                                    # Try to parse various date formats
                                    try:
                                        # Clean the text
                                        clean_text = re.sub(r"[^a-zA-Z0-9,\s/-]", "", col_text).strip()
                                        
                                        # Try different date parsing approaches
                                        date_formats = [
                                            "%a, %d %B",
                                            "%d %B %Y",
                                            "%d/%m/%Y",
                                            "%d-%m-%Y",
                                            "%B %d, %Y"
                                        ]
                                        
                                        for fmt in date_formats:
                                            try:
                                                parsed_date = datetime.strptime(clean_text, fmt)
                                                if fmt == "%a, %d %B":  # Add year if missing
                                                    if parsed_date.replace(year=current_year) < datetime.now():
                                                        parsed_date = parsed_date.replace(year=current_year + 1)
                                                    else:
                                                        parsed_date = parsed_date.replace(year=current_year)
                                                collection_date = parsed_date.strftime("%d/%m/%Y")
                                                break
                                            except ValueError:
                                                continue
                                        
                                        if collection_date:
                                            break
                                    except Exception:
                                        continue
                        
                        # Add to data if we have both type and date
                        if container_type and collection_date and container_type.lower() != "unknown":
                            data["bins"].append({
                                "type": container_type,
                                "collectionDate": collection_date
                            })
                except Exception as e:
                    print(f"Error processing row: {e}")
                    continue
            
            # If no data found, add a debug entry
            if not data["bins"]:
                print("No bin collection data found. Page source:")
                print(driver.page_source[:1000])  # Print first 1000 chars for debugging

        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            print(f"Full address used: {full_address}")
            print(f"Page URL: {page}")
            # Add some debug information
            if driver:
                print(f"Current page title: {driver.title}")
                print(f"Current URL: {driver.current_url}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return data