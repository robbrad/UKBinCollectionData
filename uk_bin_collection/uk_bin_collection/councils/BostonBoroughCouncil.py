import time

from bs4 import BeautifulSoup
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)
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
            data = {"bins": []}
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get("https://www.boston.gov.uk/findwastecollections")

            # Wait for initial page load and Cloudflare bypass
            WebDriverWait(driver, 30).until(
                lambda d: "Just a moment" not in d.title and d.title != ""
            )
            time.sleep(3)

            # Try to accept cookies if the banner appears
            try:
                accept_button = WebDriverWait(driver, timeout=30).until(
                    EC.element_to_be_clickable((By.NAME, "acceptall"))
                )
                accept_button.click()
                time.sleep(2)
            except (
                TimeoutException,
                NoSuchElementException,
                ElementClickInterceptedException,
            ):
                # Cookie banner not present or not clickable; continue without accepting
                pass

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.ID, "BBCWASTECOLLECTIONS_START_SEARCHPOSTCODE")
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "BBCWASTECOLLECTIONS_START_START10_NEXT")
                )
            )
            findAddress.click()

            # Wait for the custom dropdown container to be visible
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.ID, "BBCWASTECOLLECTIONS_COLLECTIONADDRESS_INCIDENTUPRN_chosen")
                )
            )

            # Click on the dropdown to open it
            dropdown = driver.find_element(
                By.ID, "BBCWASTECOLLECTIONS_COLLECTIONADDRESS_INCIDENTUPRN_chosen"
            )
            dropdown.click()

            # Wait for the dropdown options to be visible
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "chosen-results"))
            )

            # Locate the desired option using its text
            desired_option = driver.find_element(
                By.XPATH,
                "//li[@class='active-result' and contains(text(), '"
                + user_paon
                + "')]",
            )

            # Click on the desired option
            desired_option.click()

            # dropdown.select_by_visible_text(user_paon)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "BBCWASTECOLLECTIONS_COLLECTIONADDRESS_NEXT3_NEXT")
                )
            )
            findAddress.click()

            # Wait for the collections table to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "BBCWASTECOLLECTIONS_SERVICE_FIELD859_OUTER")
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Find the container with the bin information
            bins = soup.find_all(
                "div", class_="grid__cell grid__cell--listitem grid__cell--cols1"
            )

            current_year = datetime.now().year
            next_year = current_year + 1

            # Loop through each bin container to extract the details
            for bin_div in bins:
                # Find the bin type (title text)
                bin_type = bin_div.find("h2", class_="item__title").text.strip()

                # Find the next collection date
                next_collection = (
                    bin_div.find("div", class_="item__content")
                    .find("div")
                    .text.strip()
                    .replace("Next: ", "")
                )

                next_collection = datetime.strptime(
                    remove_ordinal_indicator_from_date_string(next_collection),
                    "%A %d %B",
                )

                if (datetime.now().month == 12) and (next_collection.month == 1):
                    next_collection = next_collection.replace(year=next_year)
                else:
                    next_collection = next_collection.replace(year=current_year)

                dict_data = {
                    "type": bin_type,
                    "collectionDate": next_collection.strftime(date_format),
                }
                data["bins"].append(dict_data)

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
