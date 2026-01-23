import logging
import pickle
import time

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_postcode(user_postcode)
            url = "https://bins.uttlesford.gov.uk/"

            # Get session cookies using requests

            user_agent = """general.useragent.override", "userAgent=Mozilla/5.0 
            (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like 
            Gecko) CriOS/101.0.4951.44 Mobile/15E148 Safari/604.1"""

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, user_agent, __name__)

            # Navigate to the page first
            driver.get(url)

            wait = WebDriverWait(driver, 60)

            logging.info("Entering postcode")
            input_element_postcode = wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[@id="postcode"]'))
            )

            input_element_postcode.send_keys(user_postcode)
            input_element_postcode.send_keys(Keys.ENTER)

            logging.info("Searching for postcode")
            input_element_postcode_dd = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//select[@id="housenn"]'))
            )

            logging.info("Selecting address")
            drop_down_values = Select(input_element_postcode_dd)

            drop_down_values.select_by_visible_text(str(user_paon))

            input_element_address_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//input[@alt="View your waste collection days"]')
                )
            )

            input_element_address_btn.click()

            logging.info("Waiting for bin collection page")
            h3_element = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h3[contains(text(), 'Future Collection Dates')]")
                )
            )

            logging.info("Extracting bin collection data")
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            bins = []
            rows = soup.select("div.wrap table tbody tr")

            for row in rows:
                cols = row.find_all("td")
                if len(cols) == 2:
                    bin_types = [img["alt"] for img in cols[0].find_all("img")]
                    collection_date_str = cols[1].text
                    collection_date_str = remove_ordinal_indicator_from_date_string(
                        collection_date_str
                    )
                    collection_date = datetime.strptime(collection_date_str, "%A %d %B")
                    current_year = datetime.now().year
                    collection_date = collection_date.replace(year=current_year)
                    if collection_date < datetime.now():
                        collection_date = collection_date.replace(year=current_year + 1)
                    collection_date_str = collection_date.strftime("%d/%m/%Y")

                    for bin_type in bin_types:
                        bins.append(
                            {"type": bin_type, "collectionDate": collection_date_str}
                        )

            bin_data = {"bins": bins}

            return bin_data

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            raise

        finally:
            if driver:
                driver.quit()
