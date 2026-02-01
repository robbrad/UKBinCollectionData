import datetime
import time
from datetime import datetime

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
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            user_postcode = kwargs.get("postcode")
            if not user_postcode:
                raise ValueError("No postcode provided.")
            check_postcode(user_postcode)
            user_paon = kwargs.get("paon")
            if not user_paon:
                raise ValueError("No house name/number provided.")
            check_paon(user_paon)

            data = {"bins": []}

            url = "https://www.midsuffolk.gov.uk/check-your-collection-day"

            # Get our initial session running
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(url)

            wait = WebDriverWait(driver, 30)
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[aria-label="Postcode"]')
                )
            )

            # Enter postcode
            postcode_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[aria-label="Postcode"]')
                )
            )
            postcode_input.send_keys(user_postcode)

            # Click find address
            find_address_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "lfr-btn-label"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", find_address_button)
            driver.execute_script("arguments[0].click();", find_address_button)

            time.sleep(5)
            # Wait for address dropdown
            select_address_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "select"))
            )

            # Select address based on postcode and house number
            select = Select(select_address_input)
            selected = False

            for addr_option in select.options:
                if not addr_option.text or addr_option.text == "Please Select...":
                    continue

                option_text = addr_option.text.upper()
                postcode_upper = user_postcode.upper()
                paon_str = str(user_paon).upper()

                # Check if this option contains both postcode and house number
                if postcode_upper in option_text and (
                    f"{paon_str} " in option_text
                    or f", {paon_str}," in option_text
                    or f", {paon_str} " in option_text
                    or f", {paon_str}A," in option_text
                    or option_text.endswith(f", {paon_str}")
                ):
                    select.select_by_value(addr_option.get_attribute("value"))
                    selected = True
                    break

            if not selected:
                raise ValueError(
                    f"Address not found for postcode {user_postcode} and house number {user_paon}"
                )

            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.ID, "collection-cards")))

            # Parse the HTML content
            soup = BeautifulSoup(driver.page_source, "html.parser")

            collection_cards = soup.find("div", class_="collection-cards")
            if collection_cards:
                cards = collection_cards.find_all("div", class_="card")
                for card in cards:
                    collection_type = (card.find("h3")).get_text()
                    # print(collection_type)
                    p_tags = card.find_all("p")  # any <p>

                    for p_tag in p_tags:
                        if p_tag.get_text().startswith("Frequency"):
                            continue

                        # Collect text in p excluding the strong tag
                        date_str = (p_tag.get_text()).split(":")[1]

                        collection_date = datetime.strptime(date_str, "%a %d %b %Y")

                        # print(collection_date.strftime(date_format))  # Tue 03 Feb 2026

                        # Create the dictionary with the formatted data
                        dict_data = {
                            "type": collection_type,
                            "collectionDate": collection_date.strftime(date_format),
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
