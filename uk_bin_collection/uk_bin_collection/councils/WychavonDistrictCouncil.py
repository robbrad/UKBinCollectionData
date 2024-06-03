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
            data = {"bins": []}
            collections = []
            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_postcode(user_postcode)
            url = "https://selfservice.wychavon.gov.uk/wdcroundlookup/wdc_search.jsp"

            # Get session cookies using requests

            user_agent = """general.useragent.override", "userAgent=Mozilla/5.0 
            (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like 
            Gecko) CriOS/101.0.4951.44 Mobile/15E148 Safari/604.1"""

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, user_agent, __name__)

            # Navigate to the page first
            driver.get(url)

            wait = WebDriverWait(driver, 60)

            logging.info("Accepting cookies")

            try:
                logging.info("Cookies")
                cookie_window = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[@id="ccc-content"]')
                    )
                )
                time.sleep(2)
                accept_cookies = WebDriverWait(driver, timeout=10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//button[@id="ccc-recommended-settings"]')
                    )
                )
                accept_cookies.send_keys(Keys.ENTER)
                accept_cookies.click()
                accept_cookies_close = WebDriverWait(driver, timeout=10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//button[@id="ccc-close"]')
                    )
                )
                accept_cookies_close.send_keys(Keys.ENTER)
                accept_cookies_close.click()
            except:
                print(
                    "Accept cookies banner not found or clickable within the specified time."
                )
                pass

            logging.info("Entering postcode")
            input_element_postcode = wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[@id="alAddrtxt"]'))
            )

            input_element_postcode.send_keys(user_postcode)

            logging.info("Searching for postcode")
            input_element_postcode_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[@id="alAddrbtn"]'))
            )

            input_element_postcode_btn.click()

            logging.info("Waiting for address dropdown")
            input_element_postcode_dropdown = wait.until(
                EC.presence_of_element_located((By.XPATH, '//select[@id="alAddrsel"]'))
            )

            logging.info("Selecting address")
            drop_down_values = Select(input_element_postcode_dropdown)
            option_element = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, f'option[value="{str(user_uprn)}"]')
                )
            )

            driver.execute_script("arguments[0].scrollIntoView();", option_element)
            drop_down_values.select_by_value(str(user_uprn))

            input_element_address_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//input[@id="btnSubmit"]'))
            )

            input_element_address_btn.click()

            logging.info("Waiting for bin collection page")
            strong_element = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//strong[contains(text(), 'Upcoming collections')]")
                )
            )

            logging.info("Extracting bin collection data")
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            bins = []

            rows = soup.select("table tbody tr")
            for row in rows:
                bin_type = row.select_one("td:nth-of-type(2)").contents[0].strip()
                date_elements = row.select("td:nth-of-type(3) strong")
                if date_elements:
                    dates = [date.get_text(strip=True) for date in date_elements]
                else:
                    dates = ["Not applicable"]

                for date in dates:
                    if date != "Not applicable":
                        # Format the date to dd/mm/yyyy
                        formatted_date = re.search(r"\d{2}/\d{2}/\d{4}", date).group(0)
                        bins.append(
                            {"type": bin_type, "collectionDate": formatted_date}
                        )

            bin_data = {"bins": bins}

            return bin_data

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            raise

        finally:
            if driver:
                driver.quit()
