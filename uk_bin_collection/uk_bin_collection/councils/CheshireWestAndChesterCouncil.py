import time

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
            data = {"bins": []}
            collections = []
            user_uprn = kwargs.get("uprn")
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless)
            driver.get(
                "https://www.cheshirewestandchester.gov.uk/residents/waste-and-recycling/your-bin-collection/collection-day"
            )
            wait = WebDriverWait(driver, 60)

            time.sleep(5)

            cookie_close_button = wait.until(
                EC.presence_of_element_located((By.ID, "ccc-close"))
            )
            cookie_close_button.click()

            find_collection_button = wait.until(
                EC.presence_of_element_located(
                    (By.LINK_TEXT, "Find your collection day")
                )
            )
            find_collection_button.click()

            iframe_presense = wait.until(
                EC.presence_of_element_located((By.ID, "fillform-frame-1"))
            )

            driver.switch_to.frame(iframe_presense)

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//input[@id="postcode_search"]')
                )
            )


            inputElement_postcode.click()

            inputElement_postcode.send_keys(user_postcode)

            # Wait for the 'Select your property' dropdown to appear and select the first result
            dropdown = wait.until(EC.element_to_be_clickable((By.ID, "Choose_Address")))

            dropdown_options = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "lookup-option"))
            )

            # Create a 'Select' for it, then select the first address in the list
            # (Index 0 is "Make a selection from the list")
            drop_down_values = Select(dropdown)
            option_element = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, f'option.lookup-option[value="{str(user_uprn)}"]')
                )
            )

            drop_down_values.select_by_value(str(user_uprn))

            span_element = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'bin-schedule-content-bin-card'))
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            bin_cards = soup.find_all("div", {"class": "bin-schedule-content-bin-card"})
            collections = []

            # Extract bin collection information
            for card in bin_cards:
                bin_info = card.find("div", {"class": "bin-schedule-content-info"})
                bin_name = bin_info.find_all("p")[0].text.strip() + " bin"
                bin_date_str = bin_info.find_all("p")[1].text.split(":")[1].strip()
                bin_date = datetime.strptime(bin_date_str, "%A, %d %B %Y")
                collections.append((bin_name, bin_date))

            # Sort the collection data by date
            ordered_data = sorted(collections, key=lambda x: x[1])

            # Format the data as required
            data = {"bins": []}
            for item in ordered_data:
                dict_data = {
                    "type": item[0].capitalize(),
                    "collectionDate": item[1].strftime(date_format),
                }
                data["bins"].append(dict_data)

            return data

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
