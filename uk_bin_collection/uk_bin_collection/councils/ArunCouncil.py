import re
import time

from bs4 import BeautifulSoup
from selenium import webdriver
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

    @staticmethod
    def _pick_address_option(options: list, house_number: str) -> str:
        """Return the one option whose text starts with house_number as a whole word.

        Raises ValueError when none, or more than one, option matches.
        """
        wanted = house_number.strip().upper()
        pattern = re.compile(rf"^{re.escape(wanted)}(?![A-Z0-9])")
        matches = [text for text in options if pattern.match(text.strip().upper())]
        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one address starting with '{house_number}', "
                f"found {len(matches)}: {matches or options}"
            )
        return matches[0]

    def parse_data(self, page: str, **kwargs) -> dict:
        try:
            # Make a BS4 object
            data = {"bins": []}

            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            driver = create_webdriver(web_driver, headless, None, __name__)
            page = "https://www1.arun.gov.uk/when-are-my-bins-collected/"
            check_paon(user_paon)
            check_postcode(user_postcode)
            driver.get(page)

            start_now_button = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located((By.LINK_TEXT, "Start now"))
            )
            start_now_button.click()

            # Wait for the postcode field to appear then populate it
            input_element_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "postcode"))
            )
            input_element_postcode.send_keys(user_postcode)

            continue_button = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "govuk-button"))
            )
            continue_button.click()

            # The address page loads after the postcode submit; wait for it
            # rather than looking the dropdown up straight away.
            address_dropdown = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "address"))
            )
            address_selection_menu = Select(address_dropdown)
            selected_address = self._pick_address_option(
                [option.text for option in address_selection_menu.options], user_paon
            )
            address_selection_menu.select_by_visible_text(selected_address)

            continue_button = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "govuk-button"))
            )
            continue_button.click()
            # Check for text saying "Next collection dates"
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(text(), 'Next collection dates')]")
                )
            )

            soup = BeautifulSoup(driver.page_source, "html.parser")
            soup.prettify()
            table = soup.find("table", class_="govuk-table")

            for row in table.find("tbody").find_all("tr"):
                # Extract the type of collection and the date of next collection
                collection_type = (
                    row.find("th", class_="govuk-table__header").text.strip().split(" ")
                )[0]
                collection_date = row.find(
                    "td", class_="govuk-table__cell"
                ).text.strip()

                # Append the information to the data structure
                data["bins"].append(
                    {"type": collection_type, "collectionDate": collection_date}
                )

        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception.
            if driver:
                driver.quit()
        return data
