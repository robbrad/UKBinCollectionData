# This script pulls (in one hit) the data from Bromley Council Bins Data
import datetime
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        """
        Fetch and parse bin collection data for a given address from Brighton & Hove's collections page.
        
        This function drives a Selenium browser to the fixed Brighton & Hove collections URL, submits the provided postcode, selects the matching PAON (primary addressable object name) from the resulting address dropdown, submits the selection, and parses the resulting list view into structured bin collection entries.
        
        Parameters:
            page (str): Unused; included for compatibility with caller signature.
            uprn (str, optional): Unique Property Reference Number for the address (passed via kwargs).
            paon (str, optional): Primary addressable object name used to match and select the address from dropdown (passed via kwargs).
            postcode (str, optional): Postcode to search on the council site (passed via kwargs).
            web_driver (str or WebDriver, optional): Specification or instance used by create_webdriver to start the browser (passed via kwargs).
            headless (bool, optional): Whether to run the browser in headless mode (passed via kwargs).
        
        Returns:
            dict: A dictionary with a single key "bins" whose value is a list of objects each containing:
                - "type": bin type string
                - "collectionDate": collection date string formatted according to the module's date_format
        
        Raises:
            Exception: If no dropdown option matching `paon` is found or any other error occurs during navigation or parsing.
        """
        driver = None
        try:
            data = {"bins": []}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}
            url = "https://enviroservices.brighton-hove.gov.uk/link/collections"
            uprn = kwargs.get("uprn")
            user_paon = kwargs.get("paon")
            postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(url)

            wait = WebDriverWait(driver, 60)
            post_code_search = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "form-control"))
            )
            post_code_search.send_keys(postcode)

            submit_btn = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//button[contains(@class, 'mx-name-actionButton3')]")
                )
            )

            submit_btn.send_keys(Keys.ENTER)

            dropdown_options = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f'//option[contains(text(), "{user_paon}")]')
                )
            )
            parent_element = dropdown_options.find_element(
                By.XPATH, ".."
            )  # Using ".." to move up to the parent element

            # Create a 'Select' for it, then select the first address in the list
            # (Index 0 is "Make a selection from the list")
            options = parent_element.find_elements(By.TAG_NAME, "option")
            found = False
            for option in options:
                if user_paon in option.text:
                    option.click()
                    found = True
                    break

            if not found:
                raise Exception(
                    f"Address containing '{user_paon}' not found in dropdown options"
                )

            submit_btn = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//button[contains(@class, 'mx-name-actionButton5')]")
                )
            )

            submit_btn.send_keys(Keys.ENTER)

            results = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f'//div[contains(@class,"mx-name-listView1")]')
                )
            )

            # Make a BS4 object
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            # Initialize current month and year (you can modify these values based on your requirement)
            data = {"bins": []}

            current_date = datetime.now()

            # Find all elements with class starting with 'mx-name-index-'
            bin_view = soup.find(class_="mx-name-listView1")
            bins = bin_view.find_all(
                class_=lambda x: x and x.startswith("mx-name-index-")
            )

            for bin_item in bins:
                bin_type = bin_item.find(class_="mx-name-text31").text.strip()

                bin_date_str = bin_item.find(class_="mx-name-text29").text.strip()

                bin_date = datetime.strptime(bin_date_str, "%d %B %Y")
                bin_date = bin_date.strftime(date_format)

                dict_data = {"type": bin_type, "collectionDate": bin_date}
                data["bins"].append(dict_data)
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