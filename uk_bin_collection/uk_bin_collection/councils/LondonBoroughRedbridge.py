import re
import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass

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
        data = {"bins": []}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}

        uprn = kwargs.get("uprn")
        postcode = kwargs.get("postcode")
        web_driver = kwargs.get("web_driver")
        driver = create_webdriver(web_driver)
        driver.get(kwargs.get("url"))

        wait = WebDriverWait(driver, 60)
        post_code_search = wait.until(
            EC.presence_of_element_located((By.XPATH, f"//input[contains(@class, 'searchAddress')]"))
        )
        post_code_search.send_keys(postcode)

        submit_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, f"//button[contains(@class, 'searchAddressButton')]"))
        )

        submit_btn.send_keys(Keys.ENTER)

        address_link = wait.until(
            EC.presence_of_element_located((By.XPATH, f'//a[contains(@data-uprn,"{uprn}")]'))
        )

        address_link.send_keys(Keys.ENTER)

        address_results = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, 'your-collection-schedule-container'))
        )


        # Make a BS4 object
        soup = BeautifulSoup(driver.page_source, features="html.parser")
        data = {"bins": []}

        # Get the current month and year
        current_month = datetime.now().month
        current_year = datetime.now().year

        # Function to extract collection data
        def extract_collection_data(collection_div, collection_type):
            if collection_div:
                date_element = collection_div.find(class_='recycling-collection-day-numeric') or collection_div.find(
                    class_='refuse-collection-day-numeric') or collection_div.find(class_='garden-collection-day-numeric')
                month_element = collection_div.find(class_='recycling-collection-month') or collection_div.find(
                    class_='refuse-collection-month') or collection_div.find(class_='garden-collection-month')

                if date_element and month_element:
                    collection_date = date_element.get_text(strip=True)
                    collection_month = month_element.get_text(strip=True)

                    # Combine month, date, and year into a string
                    date_string = f"{collection_date} {collection_month} {current_year}"

                    try:
                        # Convert the date string to a datetime object
                        collection_date_obj = datetime.strptime(date_string, '%d %B %Y')

                        # Check if the month is ahead of the current month
                        if collection_date_obj.month >= current_month:
                            # If the month is ahead, use the current year
                            formatted_date = collection_date_obj.strftime(date_format)
                        else:
                            # If the month is before the current month, use the next year
                            formatted_date = collection_date_obj.replace(year=current_year + 1).strftime(date_format)
                        # Create a dictionary for each collection entry
                        dict_data = {
                            "type": collection_type,
                            "collectionDate": formatted_date
                        }

                        # Append dictionary data to the 'bins' list in the 'data' dictionary
                        data["bins"].append(dict_data)

                    except ValueError as e:
                        # Handle the case where the date format is invalid
                        formatted_date = "Invalid Date Format"

        # Extract Recycling collection data
        extract_collection_data(soup.find(class_='container-fluid RegularCollectionDay').find_next_sibling('div'), "Recycling")

        # Extract Refuse collection data
        for refuse_div in soup.find_all(class_='container-fluid RegularCollectionDay'):
            extract_collection_data(refuse_div, "Refuse")

        # Extract Garden Waste collection data
        extract_collection_data(soup.find(class_='container-fluid gardenwasteCollectionDay'), "Garden Waste")

        # Print the extracted data
        return data