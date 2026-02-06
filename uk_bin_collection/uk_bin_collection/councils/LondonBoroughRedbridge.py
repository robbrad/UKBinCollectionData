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

            # Function to extract collection data from multiple dates from multiple dates
            def extract_collection_data(collection_div, collection_type, class_prefix):
                if collection_div:
                    # Find all date containers
                    date_containers = collection_div.find_all(
                        class_="garden-collection-postdate"
                    )

                    for container in date_containers:
                        # Find date and month elements with the appropriate prefix
                        date_element = container.find(
                            class_=f"{class_prefix}-garden-collection-day-numeric"
                        )
                        month_element = container.find(
                            class_=f"{class_prefix}-collection-month"
                        )

                        if date_element and month_element:
                            collection_date = date_element.get_text(strip=True)
                            collection_month = month_element.get_text(
                                strip=True
                            )  # e.g., "February 2026 "

                            # Parse the date string (format: "04 February 2026 ")
                            date_string = f"{collection_date} {collection_month.strip()}"

                            try:
                                # Convert the date string to a datetime object
                                collection_date_obj = datetime.strptime(
                                    date_string, "%d %B %Y"
                                )

                                # Format the date
                                formatted_date = collection_date_obj.strftime(
                                    date_format
                                )

                                # Create a dictionary for each collection entry
                                dict_data = {
                                    "type": collection_type,
                                    "collectionDate": formatted_date,
                                }

                                # Append dictionary data to the 'bins' list in the 'data' dictionary
                                data["bins"].append(dict_data)

                            except ValueError as e:
                                # Handle the case where the date format is invalid
                                print(
                                    f"Error parsing date '{date_string}' for {collection_type}: {e}"
                                )

            # Extract Refuse collection data
            refuse_div = soup.find(
                "div", class_="container-fluid RegularCollectionDay"
            )
            if refuse_div and refuse_div.find(class_="refuse-container"):
                extract_collection_data(refuse_div, "Refuse", "refuse")

            # Extract Recycling collection data
            recycling_divs = soup.find_all(
                "div", class_="container-fluid RegularCollectionDay"
            )
            for div in recycling_divs:
                if div.find(class_="recycle-container"):
                    extract_collection_data(div, "Recycling", "recycling")
                    break

            # Extract Garden Waste collection data
            garden_div = soup.find(
                "div", class_="container-fluid gardenwasteCollectionDay"
            )
            if garden_div:
                extract_collection_data(garden_div, "Garden Waste", "garden")

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
