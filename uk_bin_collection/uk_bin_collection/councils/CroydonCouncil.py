import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

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
            user_postcode = kwargs.get("postcode")
            if not user_postcode:
                raise ValueError("No postcode provided.")
            check_postcode(user_postcode)

            user_paon = kwargs.get("paon")
            check_paon(user_paon)
            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            driver = create_webdriver(web_driver, headless, None, __name__)
            page = "https://service.croydon.gov.uk/wasteservices/w/webpage/bin-day-enter-address"

            driver.maximize_window()

            driver.get(page)

            postcode_input = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'input[data-ts_identifier="postcode_input"]')
                )
            )

            postcode_input.send_keys(user_postcode + Keys.ENTER)

            time.sleep(5)
            # Wait for address box to be visible
            select_address_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'select[data-ts_identifier="address_selection"]')
                )
            )

            # Select address based on house number (paon)
            select = Select(select_address_input)
            paon = str(user_paon)  # Ensure paon is a string for comparison
            address_found = False

            for option in select.options:
                # Look for house number pattern with surrounding spaces to avoid partial matches
                if f" {paon} " in f" {option.text} ":
                    select.select_by_value(option.get_attribute("value"))
                    address_found = True
                    break

            if not address_found:
                raise ValueError(
                    f"Address with house number {paon} not found in the dropdown."
                )

            # Click the "Next" button
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'input[type="submit"][value="Next"]')
                )
            )
            next_button.click()

            # Wait for the bin collection content to load
            collection_content = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        '//*[@id="mats_content_wrapper"]/div[2]/div[2]/div[2]/div/div[1]/div/div[3]/div/div/div/div',
                    )
                )
            )

            soup = BeautifulSoup(driver.page_source, "html.parser")

            bin_data = {"bins": []}

            # Find all bin collection sections
            bin_sections = soup.find_all("div", {"class": "listing_template_record"})

            for section in bin_sections:
                # Get bin type from h2 tag
                bin_type_elem = section.find("h2")
                if bin_type_elem:
                    bin_type = bin_type_elem.text.strip()

                    # Find collection date span
                    date_span = section.find("span", {"class": "value-as-text"})
                    if date_span:
                        collection_date_string = date_span.text.strip()

                        # Convert date string to required format
                        try:
                            # Parse the date string (e.g., "Sunday 1 June 2025")
                            parsed_date = datetime.strptime(
                                collection_date_string, "%A %d %B %Y"
                            )
                            # Format as dd/mm/yyyy
                            formatted_date = parsed_date.strftime("%d/%m/%Y")

                            # Create bin entry
                            bin_info = {
                                "type": bin_type,
                                "collectionDate": formatted_date,
                            }
                            bin_data["bins"].append(bin_info)
                        except ValueError as e:
                            print(f"Error parsing date '{collection_date_string}': {e}")

            if not bin_data["bins"]:
                raise ValueError("No bin collection data found")

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
