import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
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

            time.sleep(5)

            inputElement_postcodesearch.send_keys(Keys.TAB + Keys.DOWN)

            dropdown = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//div[contains(text(), ' {user_paon}')]")
                )
            )
            dropdown.click()

            # This website is horrible!
            WebDriverWait(driver, 20).until(
                EC.text_to_be_present_in_element(
                    (By.CSS_SELECTOR, "div.col-collection-panel"), "Next collection"
                )
            )

            # Even then it can still be adding data to the page...
            time.sleep(5)

            # Scraping via Selenium rather than BeautifulSoup, to ensure eveything's loaded
            collection_panels = driver.find_elements(
                By.CSS_SELECTOR, "div.col-collection-panel"
            )

            for panel in collection_panels:
                try:
                    # Get bin type (e.g., General waste, Food waste)
                    bin_type = panel.find_element(
                        By.CSS_SELECTOR, "h3.collectionDataHeader"
                    ).text.strip()
                    # Get next collection date
                    lines = panel.find_elements(By.CSS_SELECTOR, "ul li")
                    for line in lines:
                        if "Next collection" in line.text:
                            date_str = (
                                line.text.split("Next collection")[1]
                                .strip(": ")
                                .strip()
                            )
                            bin_date = datetime.strptime(date_str, "%d/%m/%Y")
                            bin_data["bins"].append(
                                {
                                    "type": bin_type,
                                    "collectionDate": bin_date.strftime(date_format),
                                }
                            )
                except Exception as inner_e:
                    print(f"Skipping one panel due to error: {inner_e}")

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
