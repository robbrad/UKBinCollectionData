import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# import the wonderful Beautiful Soup and the URL grabber
import re


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            page = "https://community.fdean.gov.uk/s/waste-collection-enquiry"

            data = {"bins": []}

            house_number = kwargs.get("paon")
            postcode = kwargs.get("postcode")
            full_address = f"{house_number}, {postcode}"
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            # If you bang in the house number (or property name) and postcode in the box it should find your property
            wait = WebDriverWait(driver, 60)
            address_entry_field = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@placeholder="Search Properties..."]')
                )
            )

            address_entry_field.send_keys(str(full_address))

            address_entry_field = wait.until(
                EC.element_to_be_clickable((By.XPATH, f'//*[@title="{full_address}"]'))
            )
            address_entry_field.click()

            next_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//lightning-button/button[contains(text(), 'Next')]")
                )
            )
            next_button.click()

            result = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        '//table[@class="slds-table slds-table_header-fixed slds-table_bordered slds-table_edit slds-table_resizable-cols"]',
                    )
                )
            )

            # Make a BS4 object
            soup = BeautifulSoup(
                result.get_attribute("innerHTML"), features="html.parser"
            )  # Wait for the 'Select your property' dropdown to appear and select the first result

            data = {"bins": []}
            today = datetime.now()
            current_year = today.year

            # Find all bin rows in the table
            rows = soup.find_all("tr", class_="slds-hint-parent")

            for row in rows:
                try:
                    bin_type_cell = row.find("th")
                    date_cell = row.find("td")

                    if not bin_type_cell or not date_cell:
                        continue

                    container_type = bin_type_cell.get("data-cell-value", "").strip()
                    raw_date_text = date_cell.get("data-cell-value", "").strip()

                    # Handle relative values like "Today" or "Tomorrow"
                    if "today" in raw_date_text.lower():
                        parsed_date = today
                    elif "tomorrow" in raw_date_text.lower():
                        parsed_date = today + timedelta(days=1)
                    else:
                        # Expected format: "Thu, 10 April"
                        # Strip any rogue characters and try parsing
                        cleaned_date = re.sub(r"[^\w\s,]", "", raw_date_text)
                        try:
                            parsed_date = datetime.strptime(cleaned_date, "%a, %d %B")
                            parsed_date = parsed_date.replace(year=current_year)
                            if parsed_date < today:
                                # Date has passed this year, must be next year
                                parsed_date = parsed_date.replace(year=current_year + 1)
                        except Exception as e:
                            print(f"Could not parse date '{cleaned_date}': {e}")
                            continue

                    formatted_date = parsed_date.strftime(date_format)
                    data["bins"].append(
                        {"type": container_type, "collectionDate": formatted_date}
                    )

                except Exception as e:
                    print(f"Error processing row: {e}")
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
