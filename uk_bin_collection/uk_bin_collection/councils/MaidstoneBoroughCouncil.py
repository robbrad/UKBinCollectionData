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
            page = "https://my.maidstone.gov.uk/service/Find-your-bin-day"
            bin_data = {"bins": []}
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_postcode(user_postcode)
            
            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            iframe_presense = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "fillform-frame-1"))
            )
            driver.switch_to.frame(iframe_presense)

            wait = WebDriverWait(driver, 60)
            
            # Postal code input
            inputElement_postcodesearch = wait.until(
                EC.element_to_be_clickable((By.NAME, "postcode"))
            )
            inputElement_postcodesearch.send_keys(user_postcode)
            
            # Wait for the 'Select address' dropdown to be updated
            dropdown_select = wait.until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Select...')]"))
            )
            dropdown_select.click()
            
            dropdown = wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//div[contains(text(), ' {user_paon}')]"))
            )
            dropdown.click()

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
