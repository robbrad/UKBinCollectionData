import time
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dateutil.parser import parse

from uk_bin_collection.uk_bin_collection.common import create_webdriver, date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def wait_for_element_conditions(self, driver, conditions, timeout: int = 5):
        try:
            WebDriverWait(driver, timeout).until(conditions)
        except TimeoutException:
            print("Timed out waiting for page to load")
            raise

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            page = "https://sevenoaks-dc-host01.oncreate.app/w/webpage/waste-collection-day"

            # Assign user info
            user_postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless)
            driver.get(page)

            # Enter postcode
            postcode_css_selector = "#address_search_postcode"
            self.wait_for_element_conditions(
                driver,
                EC.presence_of_element_located((By.CSS_SELECTOR, postcode_css_selector)),
            )
            postcode_input_box = driver.find_element(By.CSS_SELECTOR, postcode_css_selector)
            postcode_input_box.send_keys(user_postcode)
            postcode_input_box.send_keys(Keys.ENTER)

            # Select the dropdown
            self.wait_for_element_conditions(
                driver, EC.presence_of_element_located((By.XPATH, "//select/option[2]"))
            )
            select_address_dropdown = Select(driver.find_element(By.XPATH, "//select"))

            if user_paon is not None:
                for option in select_address_dropdown.options:
                    if user_paon in option.text:
                        select_address_dropdown.select_by_visible_text(option.text)
                        break
            else:
                # If we've not been supplied an address, pick the second entry
                select_address_dropdown.select_by_index(1)

            # Grab the response blocks
            response_xpath_selector = "//div[@data-class_name]//h4/../../../.."
            self.wait_for_element_conditions(
                driver, EC.presence_of_element_located((By.XPATH, response_xpath_selector))
            )
            elements = driver.find_elements(By.XPATH, response_xpath_selector)

            # Iterate through them
            data = {"bins": []}
            for element in elements:
                try:
                    raw_bin_name = element.find_element(By.TAG_NAME, "h4").text
                    raw_next_collection_date = element.find_elements(
                        By.XPATH, ".//div[input]"
                    )[1].text

                    parsed_bin_date = parse(
                        raw_next_collection_date, fuzzy_with_tokens=True
                    )[0]

                    dict_data = {
                        "type": raw_bin_name,
                        "collectionDate": parsed_bin_date.strftime(date_format),
                    }

                    data["bins"].append(dict_data)

                except (IndexError, NoSuchElementException):
                    print("Error finding element for bin")
        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return data
