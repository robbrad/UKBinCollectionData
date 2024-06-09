import logging
import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete class for Mid-Sussex District Council implementing AbstractGetBinDataClass.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            data = {"bins": []}
            collections = []
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)

            driver.get("https://www.midsussex.gov.uk/waste-recycling/bin-collection/")
            wait = WebDriverWait(driver, 60)

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

            def click_element(by, value):
                element = wait.until(EC.element_to_be_clickable((by, value)))
                driver.execute_script("arguments[0].scrollIntoView();", element)
                element.click()

            logging.info("Entering postcode")
            input_element_postcode = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//input[@id="PostCodeStep_strAddressSearch"]')
                )
            )

            input_element_postcode.send_keys(user_postcode)

            logging.info("Entering postcode")

            click_element(By.XPATH, "//button[contains(text(), 'Search')]")

            logging.info("Selecting address")
            dropdown = wait.until(
                EC.element_to_be_clickable((By.ID, "StrAddressSelect"))
            )

            dropdown_options = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//select[@id='StrAddressSelect']/option")
                )
            )
            dropdownSelect = Select(dropdown)
            dropdownSelect.select_by_visible_text(str(user_paon))

            click_element(By.XPATH, "//button[contains(text(), 'Select')]")

            logging.info("Waiting for bin schedule")
            bin_results = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//strong[contains(text(), '{user_paon}')]")
                )
            )

            # Make a BS4 object
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Find the table with bin collection data
            table = soup.find("table", class_="collDates")
            if table:
                rows = table.find_all("tr")[1:]  # Skip the header row
            else:
                rows = []

            # Extract the data from the table and format it according to the JSON schema
            bins = []
            date_pattern = re.compile(r"(\d{2}) (\w+) (\d{4})")

            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 3:
                    print("Skipping row, not enough columns:", row)
                    continue  # Skip rows that do not have enough columns

                collection_type = cols[1].text.strip()
                collection_date = cols[2].text.strip()

                # Convert the collection date to the required format
                date_match = date_pattern.search(collection_date)
                if date_match:
                    day, month, year = date_match.groups()
                    month_number = {
                        "January": "01",
                        "February": "02",
                        "March": "03",
                        "April": "04",
                        "May": "05",
                        "June": "06",
                        "July": "07",
                        "August": "08",
                        "September": "09",
                        "October": "10",
                        "November": "11",
                        "December": "12",
                    }.get(month, "00")

                    formatted_date = f"{day}/{month_number}/{year}"
                    bins.append(
                        {"type": collection_type, "collectionDate": formatted_date}
                    )
                else:
                    print("Date pattern not found in:", collection_date)

            # Create the final JSON structure
            bin_data = {"bins": bins}
            return bin_data
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            raise

        finally:
            if driver:
                driver.quit()
