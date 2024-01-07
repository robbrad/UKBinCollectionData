from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys

import time
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
            page = "https://mybexley.bexley.gov.uk/service/When_is_my_collection_day"

            data = {"bins": []}

            user_uprn = kwargs.get("uprn")
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless)
            driver.get(page)

            # If you bang in the house number (or property name) and postcode in the box it should find your property

            iframe_presense = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "fillform-frame-1"))
            )

            driver.switch_to.frame(iframe_presense)
            wait = WebDriverWait(driver, 60)
            start_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button/span[contains(text(), 'Next')]")
                )
            )

            start_btn.click()

            inputElement_postcodesearch = wait.until(
                EC.element_to_be_clickable((By.ID, "postcode_search"))
            )
            inputElement_postcodesearch.send_keys(user_postcode)

            find_address_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="search"]'))
            )
            find_address_btn.click()

            dropdown_options = wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="select2-chosen-1"]'))
            )
            time.sleep(2)
            dropdown_options.click()
            time.sleep(1)
            dropdown_input = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="s2id_autogen1_search"]')
                )
            )
            time.sleep(1)
            dropdown_input.send_keys(user_paon)
            dropdown_input.send_keys(Keys.ENTER)

            results_found = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "found-content"))
            )
            finish_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button/span[contains(text(), 'Next')]")
                )
            )
            finish_btn.click()
            final_page = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "waste-header-container"))
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            bin_fields = soup.find_all("div", class_="waste-panel-container")
            # Define your XPath

            for bin in bin_fields:
                # Extract h3 text from the current element
                h3_text = (
                    bin.find("h3", class_="container-name").get_text(strip=True)
                    if bin.find("h3", class_="container-name")
                    else None
                )

                date_text = (
                    bin.find("p", class_="container-status").get_text(strip=True)
                    if bin.find("p", class_="container-status")
                    else None
                )

                if h3_text and date_text:
                    # Parse the date using the appropriate format
                    parsed_date = datetime.strptime(date_text, "%A %d %B")

                    # Assuming the current year is used for the collection date
                    current_year = datetime.now().year

                    # If the parsed date is in the past, assume it's for the next year
                    if parsed_date < datetime.now():
                        current_year += 1

                    data["bins"].append(
                        {
                            "type": h3_text,
                            "collectionDate": parsed_date.replace(
                                year=current_year
                            ).strftime("%d/%m/%Y"),
                        }
                    )

        
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