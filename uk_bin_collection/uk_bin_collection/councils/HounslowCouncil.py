import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_date(self, date_str):
        date_formats = [
            "This %A - %d %b %Y",  # Changed %B to %b to accommodate abbreviated month names
            "Next %A - %d %b %Y",  # Same change here
            "%A %d %b %Y",  # And here
        ]
        for format in date_formats:
            try:
                return datetime.strptime(date_str, format).strftime("%d/%m/%Y")
            except ValueError:
                continue
        raise ValueError(f"Date format not recognized: {date_str}")

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            # Make a BS4 object

            page = "https://www.hounslow.gov.uk/info/20272/recycling_and_waste_collection_day_finder"

            user_postcode = kwargs.get("postcode")
            user_uprn = kwargs.get("uprn")
            user_paon = kwargs.get("paon")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            wait = WebDriverWait(driver, 60)

            inputElement_postcodesearch = wait.until(
                EC.element_to_be_clickable((By.ID, "Postcode"))
            )

            inputElement_postcodesearch.send_keys(user_postcode)

            inputElement_postcodesearch_btn = wait.until(
                EC.element_to_be_clickable((By.ID, "findAddress"))
            )
            inputElement_postcodesearch_btn.click()

            inputElement_select_address = wait.until(
                EC.element_to_be_clickable((By.ID, "UPRN"))
            )

            select_element = wait.until(
                EC.visibility_of_element_located((By.ID, "UPRN"))
            )  # Adjust this ID to your element's ID

            # Create a Select object
            select = Select(select_element)

            # Fetch all options
            options = select.options

            # Loop through options to find the one that starts with the UPRN
            for option in options:
                if option.get_attribute("value").startswith(f"{user_uprn}|"):
                    option.click()  # Select the matching option
                    break

            results = wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "bin_day_main_wrapper"))
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            # Find all headers which include collection dates
            collection_headers = soup.find_all("h4")
            bins_data = []

            # Process each collection date and corresponding bins
            for header in collection_headers:
                date_text = header.get_text(strip=True)
                collection_date = self.parse_date(date_text)

                # Get next sibling which should be the list of bins
                bin_list = header.find_next_sibling("ul")
                if bin_list:
                    for item in bin_list.find_all("li", class_="list-group-item"):
                        bin_type = item.get_text(strip=True)
                        bins_data.append(
                            {"type": bin_type, "collectionDate": collection_date}
                        )

            # Construct the final JSON object
            json_data = {"bins": bins_data}

        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return json_data
