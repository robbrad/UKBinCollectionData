import time
from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            bindata = {"bins": []}
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            check_paon(user_paon)
            check_postcode(user_postcode)

            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.set_window_size(1920, 1080)  # 👈 ensure full viewport

            driver.get("https://www.knowsley.gov.uk/bins-waste-and-recycling/your-household-bins/putting-your-bins-out")

            # Dismiss cookie popup if it exists
            try:
                accept_cookies = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'agree-button') and contains(text(), 'Accept all cookies')]"))
                )
                accept_cookies.click()
                time.sleep(0.5)
            except:
                pass  # Cookie popup not shown

            # Step 1: Click "Search by postcode"
            search_btn = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(text(), 'Search by postcode to find out when your bins are emptied')]")
                )
            )
            search_btn.send_keys(Keys.RETURN)

            # Step 2: Enter postcode
            postcode_box = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//label[contains(text(), 'Please enter the post code')]/following-sibling::input")
                )
            )
            postcode_box.send_keys(user_postcode)

            postcode_search_btn = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//label[contains(text(), 'Please enter the post code')]/parent::div/following-sibling::button")
                )
            )
            postcode_search_btn.send_keys(Keys.RETURN)

            # Step 3: Select address from results
            address_selection_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//span[contains(text(), '{user_paon}')]/ancestor::li//button")
                )
            )
            address_selection_button.send_keys(Keys.RETURN)

            # Step 4: Wait until the bin info is present
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//label[contains(text(), 'collection')]")
                )
            )

            bin_info_container = driver.find_element(
                By.XPATH, "//label[contains(text(), 'collection')]/ancestor::div[contains(@class, 'mx-dataview-content')]")

            soup = BeautifulSoup(bin_info_container.get_attribute("innerHTML"), "html.parser")

            for group in soup.find_all("div", class_="form-group"):
                label = group.find("label")
                value = group.find("div", class_="form-control-static")
                if not label or not value:
                    continue

                label_text = label.text.strip()
                value_text = value.text.strip()

                if "bin next collection date" in label_text.lower():
                    bin_type = label_text.split(" bin")[0]
                    try:
                        collection_date = datetime.strptime(value_text, "%A %d/%m/%Y").strftime("%d/%m/%Y")
                    except ValueError:
                        continue

                    bindata["bins"].append({
                        "type": bin_type,
                        "collectionDate": collection_date,
                    })

            bindata["bins"].sort(
                key=lambda x: datetime.strptime(x["collectionDate"], "%d/%m/%Y")
            )

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()

        return bindata
