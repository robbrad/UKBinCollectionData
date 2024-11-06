import logging
import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
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
            data = {"bins": []}
            collections = []
            user_uprn = kwargs.get("uprn")
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            if headless:
                driver.set_window_size(1920, 1080)

            driver.get(
                "https://www.cheshirewestandchester.gov.uk/residents/waste-and-recycling/your-bin-collection/collection-day"
            )
            wait = WebDriverWait(driver, 60)

            def click_element(by, value):
                element = wait.until(EC.element_to_be_clickable((by, value)))
                driver.execute_script("arguments[0].scrollIntoView();", element)
                element.click()

            logging.info("Accepting cookies")
            click_element(By.ID, "ccc-close")

            logging.info("Finding collection day")
            click_element(By.LINK_TEXT, "Find your collection day")

            logging.info("Switching to iframe")
            iframe_presence = wait.until(
                EC.presence_of_element_located((By.ID, "fillform-frame-1"))
            )
            driver.switch_to.frame(iframe_presence)

            logging.info("Entering postcode")
            input_element_postcode = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//input[@id="postcode_search"]')
                )
            )
            input_element_postcode.send_keys(user_postcode)

            pcsearch_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//input[@id='postcode_search']"))
            )
            click_element(By.XPATH, "//input[@id='postcode_search']")

            logging.info("Selecting address")
            dropdown = wait.until(EC.element_to_be_clickable((By.ID, "Choose_Address")))
            dropdown_options = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "lookup-option"))
            )
            drop_down_values = Select(dropdown)
            option_element = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, f'option.lookup-option[value="{str(user_uprn)}"]')
                )
            )
            driver.execute_script("arguments[0].scrollIntoView();", option_element)
            drop_down_values.select_by_value(str(user_uprn))

            logging.info("Waiting for bin schedule")
            wait.until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "bin-schedule-content-bin-card")
                )
            )

            logging.info("Extracting bin collection data")
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            bin_cards = soup.find_all("div", {"class": "bin-schedule-content-bin-card"})
            collections = []

            for card in bin_cards:
                bin_info = card.find("div", {"class": "bin-schedule-content-info"})
                bin_name = bin_info.find_all("p")[0].text.strip() + " bin"
                bin_date_str = bin_info.find_all("p")[1].text.split(":")[1].strip()
                bin_date = datetime.strptime(bin_date_str, "%A, %B %d, %Y")
                collections.append((bin_name, bin_date))

            ordered_data = sorted(collections, key=lambda x: x[1])

            for item in ordered_data:
                dict_data = {
                    "type": item[0].capitalize(),
                    "collectionDate": item[1].strftime(date_format),
                }
                data["bins"].append(dict_data)

            logging.info("Data extraction complete")
            return data

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            raise

        finally:
            if driver:
                driver.quit()
