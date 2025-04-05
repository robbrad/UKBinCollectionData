import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

import re
from datetime import datetime

# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        try:
            # Make a BS4 object
            data = {"bins": []}

            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            driver = create_webdriver(web_driver, headless, None, __name__)
            page = "https://www.sholland.gov.uk/mycollections"
            check_uprn(user_uprn)
            check_postcode(user_postcode)
            driver.get(page)

            find_address_button = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located((By.ID, "SHDCWASTECOLLECTIONS_PAGE1_FINDADDRESSBUTTON"))
            )
            # Wait for the postcode field to appear then populate it
            postcode_input = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located((By.ID, "SHDCWASTECOLLECTIONS_PAGE1_POSTCODENEW"))
            )
            
            postcode_input.send_keys(user_postcode)

            find_address_button.click()

            # Wait until the address list contains an option with the target UPRN
            WebDriverWait(driver, timeout=20).until(
                lambda d: str(user_uprn) in [
                    option.get_attribute("value")
                    for option in Select(d.find_element(By.ID, "SHDCWASTECOLLECTIONS_PAGE1_ADDRESSLIST")).options
                ]
            )

            # Now select the UPRN
            address_selection_menu = Select(driver.find_element(By.ID, "SHDCWASTECOLLECTIONS_PAGE1_ADDRESSLIST"))
            address_selection_menu.select_by_value(str(user_uprn))

            next_button = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located((By.ID, "SHDCWASTECOLLECTIONS_PAGE1_CONTINUEBUTTON_NEXT"))
            )

            next_button.click()

            # Check for text saying "Next collection dates"
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(text(), 'Check your collection days')]")
                )
            )

            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Find the results container
            waste_blocks = soup.select("div.mycollections div.waste")

            for block in waste_blocks:
                try:
                    # Get the bin type
                    heading = block.find("h3").get_text(strip=True)
                    bin_type = heading.split(":")[0]  # e.g., "Refuse"

                    # Find the div with the next collection info
                    next_coll_div = block.find("div", class_="nextcoll")
                    if not next_coll_div:
                        continue

                    text = next_coll_div.get_text(" ", strip=True)

                    # Extract date using regex, e.g. 'Wednesday 9th April 2025'
                    match = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})\b', text)
                    if match:
                        day, month_str, year = match.groups()

                        # Convert to datetime to format as dd/mm/yyyy
                        date_obj = datetime.strptime(f"{day} {month_str} {year}", "%d %B %Y")
                        formatted_date = date_obj.strftime("%d/%m/%Y")
                    else:
                        formatted_date = "Unknown"

                    data["bins"].append({
                        "type": bin_type,
                        "collectionDate": formatted_date
                    })

                except Exception as parse_error:
                    print(f"Error parsing bin data: {parse_error}")

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
