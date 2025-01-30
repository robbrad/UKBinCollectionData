import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            # Get and check UPRN
            user_postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")
            check_paon(user_paon)
            check_postcode(user_postcode)
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            bindata = {"bins": []}

            API_URL = "https://portal.digital.ashfield.gov.uk/w/webpage/raise-case?service=bin_calendar"

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(API_URL)

            title = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "sub_page_title"))
            )

            # Wait for the postcode field to appear then populate it
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input.relation_path_type_ahead_search")
                )
            )

            inputElement_postcode = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input.relation_path_type_ahead_search")
                )
            )
            inputElement_postcode.clear()
            inputElement_postcode.send_keys(user_postcode)

            # Wait for the 'Select your property' dropdown to appear and select the first result
            dropdown = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.CLASS_NAME,
                        "result_list ",
                    )
                )
            )

            address_element = (
                WebDriverWait(driver, 10)
                .until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//li[starts-with(@aria-label, '{user_paon}')]")
                    )
                )
                .click()
            )

            search_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//input[@type='submit' and @value='Search']")
                )
            )
            search_button.click()

            time.sleep(10)

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            # Find the table by class name
            table = soup.find("table", {"class": "table listing table-striped"})

            # Iterate over each row in the tbody of the table
            for row in table.find("tbody").find_all("tr"):
                # Extract the service, day, and date for each row
                service = row.find_all("td")[0].get_text(strip=True)
                date = row.find_all("td")[2].get_text(strip=True)

                dict_data = {
                    "type": service,
                    "collectionDate": datetime.strptime(date, "%a, %d %b %Y").strftime(
                        date_format
                    ),
                }
                bindata["bins"].append(dict_data)
        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return bindata
