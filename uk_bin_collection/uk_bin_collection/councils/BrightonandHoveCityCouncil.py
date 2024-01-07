import re
import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# This script pulls (in one hit) the data from Bromley Council Bins Data
import datetime
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
import time


# import the wonderful Beautiful Soup and the URL grabber
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
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}

            uprn = kwargs.get("uprn")
            user_paon = kwargs.get("paon")
            postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            driver = create_webdriver(web_driver, headless)
            driver.get(kwargs.get("url"))

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
            dropdownSelect = Select(parent_element)
            dropdownSelect.select_by_visible_text(str(user_paon))

            submit_btn = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//button[contains(@class, 'mx-name-actionButton5')]")
                )
            )

            submit_btn.send_keys(Keys.ENTER)

            results = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f'//span[contains(@class,"collection-sub")]')
                )
            )

            # Make a BS4 object
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            # Initialize current month and year (you can modify these values based on your requirement)
            data = {"bins": []}

            current_date = datetime.now()

            # Find all elements with class starting with 'mx-name-index-'
            bins = soup.find_all(class_=lambda x: x and x.startswith("mx-name-index-"))

            for bin_item in bins:
                bin_type = bin_item.find(class_="collection-main").text.strip()
                day_of_week_elements = bin_item.find_all(class_="collection-header")
                bin_date = None

                for elem in day_of_week_elements:
                    if (
                        elem.text.strip() != bin_type
                    ):  # Avoid taking the bin type as the date
                        next_sibling = elem.find_next_sibling()
                        if next_sibling:
                            bin_date_str = next_sibling.text.strip()
                            try:
                                # Try parsing the date string in the format 'dd Month' (e.g., '30 Dec', '5 January')
                                bin_date = datetime.strptime(bin_date_str, "%d %b")
                            except ValueError:
                                try:
                                    # If the above format fails, try 'dd MonthName' (e.g., '30 December', '5 January')
                                    bin_date = datetime.strptime(bin_date_str, "%d %B")
                                except ValueError:
                                    pass

                            if bin_date:
                                # Set the year based on the logic provided
                                if bin_date.month < current_date.month:
                                    bin_date = bin_date.replace(year=current_date.year + 1)
                                else:
                                    bin_date = bin_date.replace(year=current_date.year)
                                # Format the date to the desired format
                                bin_date = bin_date.strftime("%d/%m/%Y")
                                break
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
