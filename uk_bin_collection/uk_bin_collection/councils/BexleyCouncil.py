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


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            page = "https://waste.bexley.gov.uk/waste"

            data = {"bins": []}

            user_uprn = kwargs.get("uprn")
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            wait = WebDriverWait(driver, 10)

            inputElement_postcodesearch = wait.until(
                EC.element_to_be_clickable((By.ID, "pc"))
            )
            inputElement_postcodesearch.send_keys(user_postcode)



            find_address_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="sub"]'))
            )
            find_address_btn.click()

            dropdown_options = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="address"]')
                )
            )
            time.sleep(2)
            dropdown_options.click()
            time.sleep(1)

            # Wait for the element to be clickable
            address = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f'//li[contains(text(), "{user_paon}")]')
                )
            )

            # Click the element
            address.click()


            submit_address = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="go"]')
                )
            )
            time.sleep(2)
            submit_address.click()

            results_found = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//h1[contains(text(), "Your bin days")]')
                )           
                )

            final_page = wait.until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "waste__collections")
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Find all waste services

            # Initialize the data dictionary
            data = {"bins": []}
            bin_sections = soup.find_all("h3", class_="waste-service-name")

            # Loop through each bin field
            for bin_section in bin_sections:
                # Extract the bin type (e.g., "Brown Caddy", "Green Wheelie Bin", etc.)
                bin_type = bin_section.get_text(strip=True).split("\n")[0]  # The first part is the bin type

                # Find the next sibling <dl> tag that contains the next collection information
                summary_list = bin_section.find_next("dl", class_="govuk-summary-list")

                if summary_list:
                    # Now, instead of finding by class, we'll search by text within the dt element
                    next_collection_dt = summary_list.find("dt", string=lambda text: "Next collection" in text)

                    if next_collection_dt:
                        # Find the sibling <dd> tag for the collection date
                        next_collection = next_collection_dt.find_next_sibling("dd").get_text(strip=True)

                        if next_collection:
                            try:
                                # Parse the next collection date (assuming the format is like "Tuesday 15 October 2024")
                                parsed_date = datetime.strptime(next_collection, "%A %d %B %Y")

                                # Add the bin information to the data dictionary
                                data["bins"].append({
                                    "type": bin_type,
                                    "collectionDate": parsed_date.strftime(date_format),
                                })
                            except ValueError as e:
                                print(f"Error parsing date for {bin_type}: {e}")
                        else:
                            print(f"No next collection date found for {bin_type}")
                    else:
                        print(f"No 'Next collection' text found for {bin_type}")
                else:
                    print(f"No summary list found for {bin_type}")

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
