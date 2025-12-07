import datetime
import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
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

    def extract_styles(self, style_str: str) -> dict:
        """
        Parse an inline CSS style string into a dictionary of property-value pairs.
        
        Parameters:
            style_str (str): Inline CSS style text with semicolon-separated declarations (e.g. "color: red; margin: 0;").
        
        Returns:
            dict: Mapping of CSS property names to their values, with surrounding whitespace removed from both keys and values.
        """
        return dict(
            (a.strip(), b.strip())
            for a, b in (
                element.split(":") for element in style_str.split(";") if element
            )
        )

    def parse_data(self, page: str, **kwargs) -> dict:
        """
        Fetches bin collection dates from the Northumberland council postcode lookup and returns them as structured entries.
        
        Parameters:
            page (str): Ignored; the method uses the council postcode lookup URL.
            **kwargs:
                postcode (str): UK postcode to query.
                uprn (str|int): Property UPRN; will be padded to 12 digits before use.
                web_driver: Optional Selenium WebDriver factory or identifier passed to create_webdriver.
                headless (bool): Optional flag controlling headless browser creation.
        
        Returns:
            dict: A dictionary with a "bins" key mapping to a list of entries. Each entry is a dict with:
                - "type" (str): The bin type (e.g., "General waste", "Recycling", "Garden waste").
                - "collectionDate" (str): The collection date formatted according to the module's date_format.
        """
        driver = None
        try:
            page = "https://bincollection.northumberland.gov.uk/postcode"

            data = {"bins": []}

            user_postcode = kwargs.get("postcode")
            user_uprn = kwargs.get("uprn")

            check_postcode(user_postcode)
            check_uprn(user_uprn)
            user_uprn = str(user_uprn).zfill(12)

            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            # Create wait object
            wait = WebDriverWait(driver, 20)

            # Wait for and click cookie button
            cookie_button = wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "accept-all"))
            )
            cookie_button.click()

            # Wait for and find postcode input
            inputElement_pc = wait.until(
                EC.presence_of_element_located((By.ID, "postcode"))
            )

            # Enter postcode and submit
            inputElement_pc.send_keys(user_postcode)
            submit_button = wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "govuk-button"))
            )
            submit_button.click()

            # Wait for and find house number input
            selectElement_address = wait.until(
                EC.presence_of_element_located((By.ID, "address"))
            )

            dropdown = Select(selectElement_address)
            dropdown.select_by_value(user_uprn)

            # Click submit button and wait for results
            submit_button = wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "govuk-button"))
            )
            submit_button.click()

            # Wait for results to load
            route_summary = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "govuk-table"))
            )

            now = datetime.now()
            current_month = now.month
            current_year = now.year

            # Get page source after everything has loaded
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # From the table, find all rows:
            # - cell 1 is the date in format eg. 9 September (so no year value 🥲)
            # - cell 2 is the day name, not useful
            # - cell 3 is the bin type eg. "General waste", "Recycling", "Garden waste"
            rows = soup.find("tbody", class_="govuk-table__body").find_all(
                "tr", class_="govuk-table__row"
            )

            for row in rows:
                bin_type = row.find_all("td")[-1].text.strip()

                collection_date_string = row.find("th").text.strip()

                # sometimes but not always the day is written "22nd" instead of 22 so make sure we get a proper int
                collection_date_day = "".join(
                    [
                        i
                        for i in list(collection_date_string.split(" ")[0])
                        if i.isdigit()
                    ]
                )
                collection_date_month_name = collection_date_string.split(" ")[1]

                # if we are currently in Oct, Nov, or Dec and the collection month is Jan, Feb, or Mar, let's assume its next year
                if (current_month >= 10) and (
                    collection_date_month_name in ["January", "February", "March"]
                ):
                    collection_date_year = current_year + 1
                else:
                    collection_date_year = current_year

                collection_date = time.strptime(
                    f"{collection_date_day} {collection_date_month_name} {collection_date_year}",
                    "%d %B %Y",
                )

                # Add it to the data
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": time.strftime(date_format, collection_date),
                    }
                )
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        return data