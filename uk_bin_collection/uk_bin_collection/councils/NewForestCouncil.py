import logging
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
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

    def get_legacy_bins(self, page: str) -> []:

        logging.info("Extracting legacy bin collection data")
        soup = BeautifulSoup(page, features="html.parser")
        legacy_bins = []

        # Rubbish and recycling
        rubbish_recycling = soup.find(
            "span", class_="CTID-77-_ eb-77-Override-textControl"
        )
        if rubbish_recycling:
            match = re.search(r"collected weekly on (\w+)", rubbish_recycling.text)
            if match:
                day_name = match.group(1)
                next_collection = get_next_day_of_week(day_name)
                legacy_bins.append(
                    {
                        "type": "Rubbish and recycling",
                        "collectionDate": next_collection,
                    }
                )
                logging.info(f"Rubbish and Recycling: {str(next_collection)}")

        # Glass collection
        glass_collection = soup.find("span", class_="CTID-78-_ eb-78-textControl")
        if glass_collection:
            match = re.search(
                r"next collection is\s+(\d{2}/\d{2}/\d{4})", glass_collection.text
            )
            if match:
                legacy_bins.append(
                    {"type": "Glass collection", "collectionDate": match.group(1)}
                )
                logging.info(f"Glass: {str(match.group(1))}")

        # Garden waste
        garden_waste = soup.find("div", class_="eb-2HIpCnWC-Override-EditorInput")
        if garden_waste:
            match = re.search(r"(\d{2}/\d{2}/\d{4})", garden_waste.text)
            if match:
                legacy_bins.append(
                    {"type": "Garden waste", "collectionDate": match.group(1)}
                )
                logging.info(f"Garden: {str(match.group(1))}")

        # return bins
        return legacy_bins

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            bins = []
            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_postcode(user_postcode)
            url = "https://forms.newforest.gov.uk/ufs/FIND_MY_BIN_BAR.eb"

            # Get session cookies using requests

            user_agent = """general.useragent.override", "userAgent=Mozilla/5.0 
            (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like 
            Gecko) CriOS/101.0.4951.44 Mobile/15E148 Safari/604.1"""

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, user_agent, __name__)

            # Navigate to the page first
            driver.get(url)
            driver.refresh()  # important otherwise it results in too many redirects

            wait = WebDriverWait(driver, 60)

            logging.info("Entering postcode")
            input_element_postcode = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//input[@id="CTID-JmLqCKl2-_-A"]')
                )
            )

            driver.execute_script(
                "arguments[0].scrollIntoView();", input_element_postcode
            )

            logging.info(f"Entering postcode '{str(user_postcode)}'")
            # Force the value through the DOM cos send_keys just don't work for some reason :(
            driver.execute_script(
                f"arguments[0].value='{str(user_postcode)}'", input_element_postcode
            )

            logging.info("Searching for postcode")
            input_element_postcode_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//input[@type="submit"]'))
            )

            input_element_postcode_btn.click()

            logging.info("Waiting for address dropdown")
            input_element_postcode_dropdown = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//select[@id="CTID-KOeKcmrC-_-A"]')
                )
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
                EC.element_to_be_clickable((By.XPATH, '//input[@value="Submit"]'))
            )

            input_element_address_btn.click()

            # Be patient, clicks take time!
            time.sleep(2)
            # logging.info(driver.page_source)

            try:
                link_element = driver.find_element(
                    By.XPATH,
                    '//a[contains(text(),"Find your current bin collection day")]',
                )
                logging.info(
                    "Found override panel span, search for link and use old logic"
                )

                link_element.click()

                # Be patient, clicks take time!
                time.sleep(2)

                bins = self.get_legacy_bins(driver.page_source)

            except NoSuchElementException:
                logging.info("Waiting for bin collection table")
                collections_table = wait.until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            '//table[contains(@class,"eb-1j4UaesZ-tableContent")]',
                        )
                    )
                )

                soup = BeautifulSoup(driver.page_source, features="html.parser")
                rows = soup.find_all(class_="eb-1j4UaesZ-tableRow")

                for row in rows:
                    cols = row.find_all("td")
                    date_string = cols[0].findChild("div").findChild("div").get_text()
                    bin_type = cols[1].findChild("div").findChild("div").get_text()

                    col_date = datetime.strptime(date_string, "%A %B %d, %Y")
                    bins.append(
                        {
                            "type": bin_type,
                            "collectionDate": datetime.strftime(col_date, date_format),
                        }
                    )

            return {"bins": bins}

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            raise

        finally:
            if driver:
                driver.quit()
