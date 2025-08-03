from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.ui import Select

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
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            user_uprn = kwargs.get("uprn")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get("https://eastrenfrewshire.gov.uk/bin-days")

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[autocomplete='postal-code']")
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            search_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[text()='Search']")
                )
            )
            search_button.click()

            # Wait for the addresses dropdown to appear
            addresses_select = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//label[text()='Addresses']/following-sibling::select")
                )
            )
            
            # Select the appropriate address based on UPRN or house number
            select = Select(addresses_select)
            if user_uprn:
                # Select by UPRN value
                select.select_by_value(user_uprn)
            elif user_paon:
                # Select by house number/name in the text
                for option in select.options:
                    if user_paon in option.text:
                        select.select_by_visible_text(option.text)
                        break
            else:
                # Select the first non-default option
                select.select_by_index(1)

            # Click the "Find my collection dates" button
            find_dates_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[text()='Find my collection dates']")
                )
            )
            find_dates_button.click()

            # Wait for the results table to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//th[text()='Bin Type']")
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            
            # Find the table with bin collection data
            table = soup.find("th", string="Bin Type").find_parent("table")
            rows = table.find_all("tr")[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 3:
                    date_cell = cells[0].get_text().strip()
                    bin_type_cell = cells[2]
                    
                    # Only process rows that have a date
                    if date_cell:
                        # Get all text content including line breaks
                        bin_type_text = bin_type_cell.get_text(separator='\n').strip()
                        
                        # Split multiple bin types that appear on separate lines
                        bin_types = [bt.strip() for bt in bin_type_text.split('\n') if bt.strip()]
                        
                        for bin_type in bin_types:
                            dict_data = {
                                "type": bin_type,
                                "collectionDate": date_cell,
                            }
                            data["bins"].append(dict_data)

            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
            )
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        return data
