from datetime import datetime
import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        web_driver = kwargs.get("web_driver")
        headless = kwargs.get("headless")
        
        check_uprn(user_uprn)
        check_postcode(user_postcode)
        
        bindata = {"bins": []}
        driver = create_webdriver(web_driver, headless, None, __name__)
        
        try:
            driver.get("https://www.broxbourne.gov.uk/bin-collection-date")
            time.sleep(8)
            
            # Handle cookie banner with multiple attempts

            try:
                cookie_btn = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Allow all')]"))
                )
                cookie_btn.click()
            except:
                pass
            
            # Find postcode input
            postcode_input = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@autocomplete='postal-code']"))
            )
            postcode_input.clear()
            postcode_input.send_keys(user_postcode)
            
            # Press Enter to lookup
            postcode_input.send_keys(Keys.RETURN)
            
            # Select address
            address_select = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//select"))
            )
            Select(address_select).select_by_value(user_uprn)
            
            # Click Next button
            next_btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
            )
            next_btn.click()
            
            # Get results
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'When is my bin collection date?')]"))
            )
            
            table = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'When is my bin collection date?')]/following::table[1]"))
            )
            
            soup = BeautifulSoup(table.get_attribute('outerHTML'), 'html.parser')
            rows = soup.find_all('tr')
            
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            for row in rows[1:]:
                columns = row.find_all('td')
                if len(columns) >= 2:
                    collection_date_text = columns[0].get_text().strip()
                    service = columns[1].get_text().strip()
                    
                    if collection_date_text:
                        try:
                            collection_date = datetime.strptime(collection_date_text, "%a %d %b")
                            if collection_date.month == 1 and current_month != 1:
                                collection_date = collection_date.replace(year=current_year + 1)
                            else:
                                collection_date = collection_date.replace(year=current_year)
                            
                            bindata["bins"].append({
                                "type": service,
                                "collectionDate": collection_date.strftime("%d/%m/%Y")
                            })
                        except ValueError:
                            continue
            
            bindata["bins"].sort(key=lambda x: datetime.strptime(x["collectionDate"], "%d/%m/%Y"))
            
        finally:
            driver.quit()
            
        return bindata