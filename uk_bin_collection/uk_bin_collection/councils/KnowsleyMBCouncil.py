import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
#import selenium keys
from selenium.webdriver.common.keys import Keys

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
            data = {"bins": []}
            collections = []
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(
                "https://www.knowsley.gov.uk/bins-waste-and-recycling/your-household-bins/putting-your-bins-out"
            )

            # Wait for the postcode field to appear then populate it
            search_btn = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(text(), 'Search by postcode to find out when your bins are emptied')]")
                )
            )
            search_btn.click()
            
            postcode_box = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//label[contains(text(), 'Please enter the post code and click \"Search for address\"')]/following-sibling::input")
                )
            )   
            
            postcode_box.send_keys(user_postcode)

            postcode_search_btn = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//label[contains(text(), 'Please enter the post code and click \"Search for address\"')]/parent::div/following-sibling::button")
                )
            )   
            postcode_search_btn.send_keys(Keys.RETURN)

            address_selection_button = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//span[contains(text(), '{user_paon}')]/ancestor::li//button")
                )
            )
            address_selection_button.send_keys(Keys.RETURN)

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//label[contains(translate(text(), 'COLLECTION', 'collection'), 'collection')]"))
            )

            # Then select the shared parent container
            bin_info_container = driver.find_element(
                By.XPATH,
                "//label[contains(translate(text(), 'COLLECTION', 'collection'), 'collection')]/ancestor::div[contains(@class, 'mx-dataview-content')]"
            )

            # Parse the HTML from the WebDriver
            soup = BeautifulSoup(bin_info_container.get_attribute("innerHTML"), features="html.parser")
            soup.prettify()
            bindata = {"bins": []}
            # All bin info is in .form-group divs with a <label> and a sibling <div>
            for group in soup.find_all("div", class_="form-group"):
                label = group.find("label")
                value = group.find("div", class_="form-control-static")

                if not label or not value:
                    continue

                label_text = label.text.strip()
                value_text = value.text.strip()

                # Only process labels containing "bin next collection date"
                if "bin next collection date" in label_text.lower():
                    bin_type = label_text.split(" bin")[0]  # e.g., "Maroon", "Grey", "Blue"
                    try:
                        collection_date = datetime.strptime(
                            value_text, "%A %d/%m/%Y"
                        ).strftime("%d/%m/%Y")
                    except ValueError:
                        continue

                    dict_data = {
                        "type": bin_type,
                        "collectionDate": collection_date,
                    }
                    bindata["bins"].append(dict_data)

            # Optional: sort by date
            bindata["bins"].sort(
                key=lambda x: datetime.strptime(x["collectionDate"], "%d/%m/%Y")
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

        return bindata
