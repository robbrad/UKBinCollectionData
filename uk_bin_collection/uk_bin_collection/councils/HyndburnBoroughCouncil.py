import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
            user_postcode = kwargs.get("postcode")
            if not user_postcode:
                raise ValueError("No postcode provided.")
            check_postcode(user_postcode)

            user_uprn = kwargs.get("uprn")
            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            driver = create_webdriver(web_driver, headless, None, __name__)
            page = "https://iapp.itouchvision.com/iappcollectionday/collection-day/?uuid=FEBA68993831481FD81B2E605364D00A8DC017A4"

            driver.get(page)

            postcode_input = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, "postcodeSearch"))
            )

            postcode_input.send_keys(user_postcode)
            postcode_input.send_keys(Keys.TAB + Keys.RETURN)

            # Wait for address box to be visible
            select_address_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        '//*[@id="addressSelect"]',
                    )
                )
            )

            # Select address based on UPRN
            select = Select(select_address_input)
            if not user_uprn:
                raise ValueError("No UPRN provided")

            try:
                select.select_by_value(str(user_uprn))
            except Exception as e:
                raise ValueError(f"Could not find address with UPRN: {user_uprn}")

            # Wait for address selection to complete
            time.sleep(5)

            # Wait for the main container with bin collection data
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.ant-row.d-flex.justify-content-between")
                )
            )

            # Verify bin collection data is loaded by checking for specific elements
            WebDriverWait(driver, 60).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "div.ant-col h3.text-white")
                )
            )

            # Remove unnecessary waits and div ID check
            time.sleep(2)  # Short wait for any final rendering

            # Continue with BeautifulSoup parsing
            soup = BeautifulSoup(driver.page_source, "html.parser")
            bin_data = {"bins": []}

            # Find all bin collection divs
            bin_divs = soup.find_all("div", class_="ant-col")

            for bin_div in bin_divs:
                # Find bin type from h3
                bin_type_elem = bin_div.find("h3", class_="text-white")
                if not bin_type_elem:
                    continue

                bin_type = bin_type_elem.text.strip()

                # Find collection date
                date_elem = bin_div.find("div", class_="text-white fw-bold")
                if not date_elem:
                    continue

                collection_date_string = date_elem.text.strip()

                # Handle date formatting
                current_date = datetime.now()
                # Parse the date string (e.g. "Monday 28 April")
                try:
                    parsed_date = datetime.strptime(
                        collection_date_string + f" {current_date.year}", "%A %d %B %Y"
                    )

                    # Check if the parsed date is in the past
                    if parsed_date.date() < current_date.date():
                        # If so, set the year to the next year
                        parsed_date = parsed_date.replace(year=current_date.year + 1)

                    formatted_date = parsed_date.strftime("%d/%m/%Y")
                    contains_date(formatted_date)

                    bin_info = {"type": bin_type, "collectionDate": formatted_date}
                    bin_data["bins"].append(bin_info)
                except ValueError as e:
                    print(f"Error parsing date {collection_date_string}: {e}")
                    continue

            if not bin_data["bins"]:
                raise ValueError("No collection data found")

            print(bin_data)

            return bin_data

        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
