import time

from bs4 import BeautifulSoup
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)
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
        """
        Retrieve bin collection types and upcoming collection dates for the given address.
        
        Parameters:
            page (str): Unused by this implementation (kept for interface compatibility).
            paon (str, in kwargs): Property/PAON text used to select the correct address option.
            postcode (str, in kwargs): Postcode to search for addresses.
            web_driver (optional, in kwargs): Selenium WebDriver instance or web driver identifier to use when creating the driver.
            headless (bool, optional, in kwargs): Whether to run the browser in headless mode.
        
        Returns:
            data (dict): Dictionary with a single key "bins" whose value is a list of dictionaries. Each entry contains:
                - "type" (str): The bin/collection type name.
                - "collectionDate" (str): The next collection date formatted according to the module's date_format.
        """
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
                accept_button = WebDriverWait(driver, timeout=10).until(
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
            # Updated field ID for V2 form
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.ID, "BBCWASTECOLLECTIONSV2_COLLECTIONS_SEARCHPOSTCODE")
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button - Updated ID for V2 form
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "BBCWASTECOLLECTIONSV2_COLLECTIONS_START10_NEXT")
                )
            )
            findAddress.click()

            # Wait for the address selection page to load
            time.sleep(3)

            # Wait for the address dropdown/selection to be available
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//select[contains(@id, 'ADDRESSSELECTION')] | //div[contains(@id, 'chosen')]")
                )
            )

            # Try to find and select the address
            # Check if it's a standard select or a chosen dropdown
            try:
                # Try standard select first
                address_select = driver.find_element(
                    By.XPATH, "//select[contains(@id, 'ADDRESSSELECTION')]"
                )
                # Find the option containing the user's PAON
                option = driver.find_element(
                    By.XPATH,
                    f"//select[contains(@id, 'ADDRESSSELECTION')]//option[contains(text(), '{user_paon}')]"
                )
                option.click()
            except NoSuchElementException:
                # Try chosen dropdown
                dropdown = driver.find_element(
                    By.XPATH, "//div[contains(@id, 'chosen')]"
                )
                dropdown.click()
                time.sleep(1)
                
                # Wait for options to be visible
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CLASS_NAME, "chosen-results"))
                )
                
                # Find and click the desired option
                desired_option = driver.find_element(
                    By.XPATH,
                    f"//li[@class='active-result' and contains(text(), '{user_paon}')]"
                )
                desired_option.click()

            # Click the next button to proceed
            next_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(@id, 'NEXT') and contains(@id, 'BBCWASTECOLLECTIONSV2')]")
                )
            )
            next_button.click()

            # Wait for the collections information to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class, 'item__title') or contains(@class, 'grid__cell--listitem')]")
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
                bin_type_elem = bin_div.find("h2", class_="item__title")
                if not bin_type_elem:
                    continue
                    
                bin_type = bin_type_elem.text.strip()

                # Find the next collection date
                content_div = bin_div.find("div", class_="item__content")
                if not content_div:
                    continue
                    
                date_div = content_div.find("div")
                if not date_div:
                    continue
                    
                next_collection = date_div.text.strip().replace("Next: ", "")

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
