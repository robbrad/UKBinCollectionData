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
            page = "https://gloucester-self.achieveservice.com/service/Bins___Check_your_bin_day"

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

            iframe_presense = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "fillform-frame-1"))
            )

            driver.switch_to.frame(iframe_presense)
            wait = WebDriverWait(driver, 60)
            inputElement_postcodesearch = wait.until(
                EC.element_to_be_clickable((By.NAME, "find_postcode"))
            )

            inputElement_postcodesearch.send_keys(user_postcode)

            # Wait for the 'Select address' dropdown to be updated
            time.sleep(2)

            dropdown = wait.until(
                EC.element_to_be_clickable((By.NAME, "chooseAddress"))
            )
            # Create a 'Select' for it, then select the first address in the list
            # (Index 0 is "Select...")
            dropdownSelect = Select(dropdown)
            dropdownSelect.select_by_value(str(user_uprn))

            # Wait for 'Searching for...' to be added to page
            WebDriverWait(driver, timeout=15).until(
                EC.text_to_be_present_in_element(
                    (By.CSS_SELECTOR, "span[data-name=html1]"), "Searching"
                )
            )

            # Wait for 'Searching for...' to be removed from page
            WebDriverWait(driver, timeout=15).until(
                EC.none_of(
                    EC.text_to_be_present_in_element(
                        (By.CSS_SELECTOR, "span[data-name=html1]"), "Searching"
                    )
                )
            )

            # Even then it can still be adding data to the page...
            time.sleep(5)

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # This is ugly but there is literally no consistency to the HTML
            def is_a_collection_date(t):
                return any("Next collection" in c for c in t.children)

            for next_collection in soup.find_all(is_a_collection_date):
                bin_info = list(
                    next_collection.parent.select_one("div:nth-child(1)").children
                )
                if not bin_info:
                    continue
                bin = bin_info[0].get_text()
                date = next_collection.select_one("strong").get_text(strip=True)
                bin_date = datetime.strptime(date, "%d %b %Y")
                dict_data = {
                    "type": bin,
                    "collectionDate": bin_date.strftime(date_format),
                }
                bin_data["bins"].append(dict_data)

            bin_data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
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
