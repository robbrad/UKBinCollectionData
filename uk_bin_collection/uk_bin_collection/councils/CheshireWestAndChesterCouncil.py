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

            time.sleep(5)

            cookie_close_button = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located((By.ID, "ccc-close"))
            )
            cookie_close_button.click()

            find_collection_button = WebDriverWait(driver, timeout=10).until(
                EC.presence_of_element_located(
                    (By.LINK_TEXT, "Find your collection day")
                )
            )
            find_collection_button.click()

            banner_close_button = WebDriverWait(driver, timeout=30).until(
                EC.presence_of_element_located((By.ID, "close-cookie-message"))
            )
            banner_close_button.click()

            time.sleep(5)

            frame = driver.find_element(
                By.XPATH, "/html/body/div[4]/section/div/div[2]/div[2]/div/iframe"
            )
            driver.switch_to.frame(frame)

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.NAME, "postcode_search"))
            )
            inputElement_postcode.send_keys(user_postcode)

            address_box_text = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "label_Choose_Address"))
            )
            address_box_text.click()
            time.sleep(2)

            address_selection_menu = Select(
                driver.find_element(By.ID, "Choose_Address")
            )
            for idx, addr_option in enumerate(address_selection_menu.options):
                option_name = addr_option.text[0 : len(user_paon)]
                if option_name == user_paon:
                    selected_address = addr_option
                    break
            address_selection_menu.select_by_visible_text(selected_address.text)

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="bin-schedule-content"]/div/h3')
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            # Get collections
            bin_cards = soup.find_all("div", {"class": "bin-schedule-content-info"})
            for card in bin_cards:
                bin_name = card.contents[0].text.strip() + " bin"
                bin_date = datetime.strptime(
                    card.contents[1].text.split(":")[1].strip(), "%A, %d %B %Y"
                )
                collections.append((bin_name, bin_date))

            ordered_data = sorted(collections, key=lambda x: x[1])
            for item in ordered_data:
                dict_data = {
                    "type": item[0].capitalize(),
                    "collectionDate": item[1].strftime(date_format),
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
