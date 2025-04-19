from time import sleep

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

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
            page = "https://www.wrexham.gov.uk/service/when-are-my-bins-collected"

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

            start_now_btn = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(text(),'Start now')]")
                )
            )
            start_now_btn.click()

            continue_without_signup_btn = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//a[contains(text(),'or, continue without an account')]",
                    )
                )
            )
            continue_without_signup_btn.click()

            iframe_presense = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "fillform-frame-1"))
            )

            driver.switch_to.frame(iframe_presense)

            inputElement_postcodesearch = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.ID, "LocationSearch"))
            )

            inputElement_postcodesearch.send_keys(user_postcode)

            # Wait for the 'Select address' dropdown to be updated

            # Wait for 'Searching for...' to be removed from page
            WebDriverWait(driver, timeout=15).until(
                EC.none_of(EC.presence_of_element_located((By.CLASS_NAME, "spinner")))
            )

            dropdown = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.ID, "ChooseAddress"))
            )
            # Create a 'Select' for it, then select the first address in the list
            # (Index 0 is "Select...")
            dropdownSelect = Select(dropdown)
            dropdownSelect.select_by_value(str(user_uprn))

            results_wait = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//th[contains(text(),'Collection')]")
                )
            )

            results = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//table[@id='wcbc_collection_details']")
                )
            )

            soup = BeautifulSoup(
                results.get_attribute("innerHTML"), features="html.parser"
            )

            for row in soup.find_all("tr")[1:]:  # Skip the header row
                date_cell, collection_cell = row.find_all("td")
                date = datetime.strptime(date_cell.text.strip(), "%d/%m/%Y").strftime(
                    date_format
                )

                for bin_item in collection_cell.find_all("li"):
                    bin_type = bin_item.text.strip()
                    bin_data["bins"].append({"type": bin_type, "collectionDate": date})

            # Optional: sort by date
            bin_data["bins"].sort(
                key=lambda x: datetime.strptime(x["collectionDate"], date_format)
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
