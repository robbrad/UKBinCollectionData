import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

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
            page = "https://tendring-self.achieveservice.com/en/service/Rubbish_and_recycling_collection_days"

            bin_data = {"bins": []}

            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_uprn(user_uprn)
            check_postcode(user_postcode)
            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            cookies_button = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located((By.ID, "close-cookie-message"))
            )
            cookies_button.click()

            without_login_button = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located(
                    (By.LINK_TEXT, "or, continue without an account")
                )
            )
            without_login_button.click()

            iframe_presense = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "fillform-frame-1"))
            )

            driver.switch_to.frame(iframe_presense)
            wait = WebDriverWait(driver, 60)
            inputElement_postcodesearch = wait.until(
                EC.element_to_be_clickable((By.NAME, "postcode_search"))
            )

            inputElement_postcodesearch.send_keys(user_postcode)

            # Wait for the 'Select address' dropdown to be updated
            time.sleep(1)

            dropdown = wait.until(
                EC.element_to_be_clickable((By.NAME, "selectAddress"))
            )
            # Create a 'Select' for it, then select the first address in the list
            # (Index 0 is "Select...")
            dropdownSelect = Select(dropdown)
            dropdownSelect.select_by_value(str(user_uprn))

            # Wait for 'wasteTable' to be shown
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "wasteTable")))

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            bins = (
                soup.find("table", {"class": "wasteTable"}).find("tbody").find_all("tr")
            )
            for bin_row in bins:
                bin = bin_row.find_all("td")
                if bin:
                    if bin[1].get_text(strip=True) != "":
                        bin_date = datetime.strptime(
                            bin[1].get_text(strip=True), "%d/%m/%Y"
                        )
                        dict_data = {
                            "type": re.sub(r"\([^)]*\)", "", bin[0].get_text(strip=True)),
                            "collectionDate": bin_date.strftime(date_format),
                        }
                        bin_data["bins"].append(dict_data)

            bin_data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
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
        return bin_data
