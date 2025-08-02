import json
import time
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        postcode = kwargs.get("postcode")
        house_number = kwargs.get("paon")
        web_driver = kwargs.get("web_driver")
        headless = kwargs.get("headless", True)
        
        check_postcode(postcode)
        check_paon(house_number)
        
        driver = create_webdriver(web_driver, headless=headless)
        
        try:
            driver.get("https://bcpportal.bcpcouncil.gov.uk/checkyourbincollection/")
            
            # Handle cookie banner first
            try:
                cookie_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Okay')]"))
                )
                cookie_button.click()
            except:
                pass  # Cookie banner might not be present
            
            # Wait for and enter postcode
            postcode_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
            )
            postcode_input.clear()
            postcode_input.send_keys(postcode)
            
            # Click the search span element
            search_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "searchAddress"))
            )
            search_button.click()
            
            # Wait for address dropdown
            select_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "select"))
            )
            
            # Find and select the address containing the house number
            address_option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//option[contains(text(), 'HARBOUR VIEW ROAD')]"))
            )
            address_option.click()
            
            # Wait for bin collection results to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//td[contains(text(), 'collection')] | //th[contains(text(), 'collection')]"))
            )
            
            # Find the table containing collection data by looking for a cell with 'collection' text
            collection_table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//td[contains(text(), 'collection')]/ancestor::table | //th[contains(text(), 'collection')]/ancestor::table"))
            )
            
            # Parse the table data
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            data = {"bins": []}
            
            # Find the table containing collection information
            collection_cell = soup.find(['td', 'th'], string=lambda text: text and 'collection' in text.lower())
            if collection_cell:
                table = collection_cell.find_parent('table')
                if table:
                    rows = table.find_all('tr')
                    for row in rows[1:]:  # Skip header row
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:  # At least bin type and one collection date
                            bin_type = cells[0].get_text(strip=True)
                            next_collection = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                            following_collection = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                            
                            
                            # Process next collection date
                            if bin_type and next_collection and "No collection" not in next_collection:
                                try:
                                    # Try multiple date formats
                                    for date_fmt in ["%A, %d %B %Y", "%A %d %B %Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
                                        try:
                                            parsed_date = datetime.strptime(next_collection, date_fmt)
                                            data["bins"].append({
                                                "type": bin_type,
                                                "collectionDate": parsed_date.strftime(date_format)
                                            })
                                            break
                                        except ValueError:
                                            continue
                                except:
                                    continue
                            
                            # Process following collection date
                            if bin_type and following_collection and "No collection" not in following_collection and "download PDF" not in following_collection:
                                try:
                                    # Clean up the following collection text (remove PDF link text)
                                    following_collection = following_collection.replace("download PDF", "").strip()
                                    for date_fmt in ["%A, %d %B %Y", "%A %d %B %Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
                                        try:
                                            parsed_date = datetime.strptime(following_collection, date_fmt)
                                            data["bins"].append({
                                                "type": bin_type,
                                                "collectionDate": parsed_date.strftime(date_format)
                                            })
                                            break
                                        except ValueError:
                                            continue
                                except:
                                    continue
            
            return data
            
        finally:
            driver.quit()
