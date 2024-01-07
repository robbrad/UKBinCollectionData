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
            uprn = kwargs.get("uprn")
            postcode = kwargs.get("postcode")
            full_address = kwargs.get("paon")

            url = "https://my.guildford.gov.uk/customers/s/view-bin-collections"

            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            driver = create_webdriver(web_driver, headless)
            driver.get(kwargs.get("url"))

            wait = WebDriverWait(driver, 120)
            post_code_search = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[contains(@class, 'slds-input')]")
                )
            )

            post_code_search.send_keys(postcode)

            post_code_submit_btn = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(@class,'slds-button')]")
                )
            )
            post_code_submit_btn.send_keys(Keys.ENTER)

            # Locate the element containing the specified address text
            address_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        f"//lightning-base-formatted-text[contains(text(), '{full_address}')]",
                    )
                )
            )

            # Find the associated radio button in the same row (preceding sibling)
            radio_button = address_element.find_element(
                By.XPATH, "../../../../preceding-sibling::td//input[@type='radio']"
            )

            radio_button.send_keys(Keys.SPACE)
            address_submit_btn = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(@name,'NEXT')]")
                )
            )
            address_submit_btn.send_keys(Keys.ENTER)

            results = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "cBinScheduleDisplay"))
            )

            results2 = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f'//div[contains(@title,"Bin Job")]')
                )
            )
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            # Find all table rows containing bin information
            rows = soup.find_all("tr", class_="slds-hint-parent")

            data = {"bins": []}

            # Extract bin type and next collection date for each row
            for row in rows:
                bin_type = (
                    row.find("td", {"data-label": "Bin Job"}).find("strong").text.strip()
                    if row.find("td", {"data-label": "Bin Job"})
                    else None
                )

                next_collection_date = (
                    row.find("td", {"data-label": "Next Collection"}).text.strip()
                    if row.find("td", {"data-label": "Next Collection"})
                    else None
                )

                if bin_type and next_collection_date:
                    # Convert date string to datetime object
                    date_format = (
                        "%A, %d %B"  # Adjust the format according to your date string
                    )
                    try:
                        next_collection_date = datetime.strptime(
                            next_collection_date, date_format
                        )

                        # Logic to determine year
                        current_date = datetime.now()
                        if next_collection_date.month < current_date.month:
                            year = current_date.year + 1
                        else:
                            year = current_date.year

                        # Format the date
                        next_collection_date = next_collection_date.replace(
                            year=year
                        ).strftime("%d/%m/%Y")
                    except ValueError:
                        pass

                    dict_data = {"type": bin_type, "collectionDate": next_collection_date}
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
