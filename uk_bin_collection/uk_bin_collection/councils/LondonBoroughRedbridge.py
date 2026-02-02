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
        driver = None
        try:
            data = {"bins": []}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}

            uprn = kwargs.get("uprn")
            postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(kwargs.get("url"))

            wait = WebDriverWait(driver, 60)
            post_code_search = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//input[contains(@class, 'searchAddress')]")
                )
            )
            post_code_search.send_keys(postcode)

            submit_btn = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//button[contains(@class, 'searchAddressButton')]")
                )
            )

            submit_btn.send_keys(Keys.ENTER)

            address_link = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f'//a[contains(@data-uprn,"{uprn}")]')
                )
            )

            address_link.send_keys(Keys.ENTER)

            wait.until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "your-collection-schedule-container")
                )
            )

            # Make a BS4 object
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            data = {"bins": []}

            # Function to extract collection data
            def extract_collection_data(collection_div, collection_type):
                if collection_div:
                    date_element = (
                        collection_div.find(
                            class_="refuse-garden-collection-day-numeric"
                        )
                        or collection_div.find(
                            class_="recycling-garden-collection-day-numeric"
                        )
                        or collection_div.find(class_="garden-collection-day-numeric")
                    )
                    month_element = (
                        collection_div.find(class_="recycling-collection-month")
                        or collection_div.find(class_="refuse-collection-month")
                        or collection_div.find(class_="garden-collection-month")
                    )

                    if date_element and month_element:
                        collection_date = date_element.get_text(strip=True)
                        collection_month = month_element.get_text(strip=True)

                        # Combine month, date, and year into a string
                        date_string = f"{collection_date} {collection_month}"

                        try:
                            # Convert the date string to a datetime object
                            formatted_date = datetime.strptime(
                                date_string, "%d %B %Y"
                            ).strftime(date_format)

                            # Create a dictionary for each collection entry
                            dict_data = {
                                "type": collection_type,
                                "collectionDate": formatted_date,
                            }

                            # Append dictionary data to the 'bins' list in the 'data' dictionary
                            data["bins"].append(dict_data)

                        except ValueError as e:
                            # Handle the case where the date format is invalid
                            formatted_date = "Invalid Date Format"

            container_fluid = soup.find_all(class_="container-fluid")
            for container in container_fluid:
                collection_type = container.find("h3").get_text().strip()
                collections = container.find_all(class_="bs3-col-sm-2")
                for collection in collections:
                    extract_collection_data(collection, collection_type)

            # Print the extracted data
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
