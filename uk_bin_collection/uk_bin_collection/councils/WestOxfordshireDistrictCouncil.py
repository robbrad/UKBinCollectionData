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
        """
        Query West Oxfordshire's waste collection site for a property's bin types and upcoming collection dates.
        
        Parameters:
            page (str): Ignored; the function always queries the West Oxfordshire waste collection enquiry page.
            paon (str, in kwargs): Property house number or name.
            postcode (str, in kwargs): Property postcode.
            web_driver (str or WebDriver, in kwargs): WebDriver identifier or instance used to create the Selenium driver.
            headless (bool, in kwargs): Whether to run the browser in headless mode.
        
        Returns:
            dict: A dictionary with a "bins" key mapping to a list of objects, each containing:
                - "type" (str): Bin/container type (e.g., "General waste", "Recycling").
                - "collectionDate" (str): Next collection date formatted as "DD/MM/YYYY".
        """
        driver = None
        try:
            page = "https://community.westoxon.gov.uk/s/waste-collection-enquiry"

            data = {"bins": []}

            house_number = kwargs.get("paon")
            postcode = kwargs.get("postcode")
            full_address = f"{house_number}, {postcode}"
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.set_window_size(1366, 768)  # Set reasonable window size for Lightning components
            driver.set_window_position(0, 0)  # Position window at top-left of screen
            driver.get(page)
            
            # Scroll to top-left to ensure components are visible
            driver.execute_script("window.scrollTo(0, 0);")

            # If you bang in the house number (or property name) and postcode in the box it should find your property
            wait = WebDriverWait(driver, 60)
            # Use XPath with placeholder attribute for more robust element selection
            address_entry_field = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//input[@placeholder="Search Properties..."]')
                )
            )
            address_entry_field.click()
            address_entry_field.send_keys(str(full_address))
            
            # Trigger dropdown by sending backspace and re-typing last character
            time.sleep(1)  # Give the search a moment to process
            address_entry_field.send_keys(Keys.BACKSPACE)
            address_entry_field.send_keys(str(full_address[len(full_address) - 1]))

            # Wait for dropdown items to appear - look for lightning-base-combobox-item elements
            # The second item contains the actual address (first is "Show more results")
            first_found_address = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '(//lightning-base-combobox-item)[2]')
                )
            )
            first_found_address.click()
            # Wait for the 'Select your property' dropdown to appear and select the first result
            next_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//lightning-button/button"))
            )
            next_btn.click()
            bin_data = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//span[contains(text(), 'Container')]")
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            rows = soup.find_all("tr", class_="slds-hint-parent")
            current_year = datetime.now().year

            for row in rows:
                columns = row.find_all("td")
                if columns:
                    container_type = row.find("th").text.strip()
                    collection_day = re.sub(
                        r"[^a-zA-Z0-9,\s]", "", columns[0].get_text()
                    ).strip()

                    if columns[0].get_text() == "Today":
                        collection_day = datetime.now().strftime("%a, %d %B")
                    elif columns[0].get_text() == "Tomorrow":
                        collection_day = (datetime.now() + timedelta(days=1)).strftime(
                            "%a, %d %B"
                        )

                    # Parse the date from the string
                    parsed_date = datetime.strptime(collection_day, "%a, %d %B")
                    if parsed_date < datetime(
                        parsed_date.year, parsed_date.month, parsed_date.day
                    ):
                        parsed_date = parsed_date.replace(year=current_year + 1)
                    else:
                        parsed_date = parsed_date.replace(year=current_year)
                    # Format the date as %d/%m/%Y
                    formatted_date = parsed_date.strftime("%d/%m/%Y")

                    # Add the bin type and collection date to the 'data' dictionary
                    data["bins"].append(
                        {"type": container_type, "collectionDate": formatted_date}
                    )
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