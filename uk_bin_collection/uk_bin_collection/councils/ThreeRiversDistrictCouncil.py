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
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            if headless:
                driver.set_window_size(1920, 1080)

            driver.get(
                "https://my.threerivers.gov.uk/en/AchieveForms/?mode=fill&consentMessage=yes&form_uri=sandbox-publish://AF-Process-52df96e3-992a-4b39-bba3-06cfaabcb42b/AF-Stage-01ee28aa-1584-442c-8d1f-119b6e27114a/definition.json&process=1&process_uri=sandbox-processes://AF-Process-52df96e3-992a-4b39-bba3-06cfaabcb42b&process_id=AF-Process-52df96e3-992a-4b39-bba3-06cfaabcb42b&noLoginPrompt=1"
            )
            wait = WebDriverWait(driver, 60)

            def click_element(by, value):
                element = wait.until(EC.element_to_be_clickable((by, value)))
                driver.execute_script("arguments[0].scrollIntoView();", element)
                element.click()

            click_element(By.XPATH, "//button[contains(text(), 'Continue')]")

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

            logging.info("Selecting address")
            dropdown = wait.until(EC.element_to_be_clickable((By.ID, "chooseAddress")))
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

            option_element = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@class="fieldContent"][1]')
                )
            )

            click_element(By.XPATH, "//button/span[contains(text(), 'Next')]")

            logging.info("Waiting for bin schedule")
            bin_results = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@data-field-name='subCollectionCalendar']//table")
                )
            )

            logging.info("Extracting bin collection data")
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            bin_cards = soup.find_all(
                "div", {"data-field-name": "subCollectionCalendar"}
            )

            bins = []

            for bin_card in bin_cards:
                # Try to find the table within the bin_card
                table = bin_card.find(
                    "table",
                    {
                        "class": "repeatable-table table table-responsive table-hover table-condensed"
                    },
                )

                if table:
                    print("Table found")
                    rows = table.select("tr.repeatable-value")
                    for row in rows:
                        cols = row.find_all("td", class_="value")
                        if len(cols) >= 3:  # Ensure there are enough columns
                            bin_type = cols[1].find_all("span")[-1].text.strip()
                            collection_date = (
                                cols[2]
                                .find_all("span")[-1]
                                .text.strip()
                                .replace("-", "/")
                            )
                            bins.append(
                                {"type": bin_type, "collectionDate": collection_date}
                            )
                else:
                    print("Table not found within bin_card")

            bin_data = {"bins": bins}
            logging.info("Data extraction complete")
            return bin_data

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            raise

        finally:
            if driver:
                driver.quit()
