import time
from datetime import datetime

from selenium.webdriver.support.ui import Select
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

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            # Make a BS4 object

            page = "https://www.chichester.gov.uk/checkyourbinday"

            user_postcode = kwargs.get("postcode")
            user_uprn = kwargs.get("uprn")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            house_number = kwargs.get("paon")

            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            wait = WebDriverWait(driver, 60)

            inputElement_postcodesearch = wait.until(
                EC.visibility_of_element_located(
                    (By.ID, "WASTECOLLECTIONCALENDARV5_CALENDAR_ADDRESSLOOKUPPOSTCODE")
                )
            )

            inputElement_postcodesearch.send_keys(user_postcode)

            inputElement_postcodesearch_btn = wait.until(
                EC.visibility_of_element_located(
                    (By.ID, "WASTECOLLECTIONCALENDARV5_CALENDAR_ADDRESSLOOKUPSEARCH")
                )
            )
            inputElement_postcodesearch_btn.send_keys(Keys.ENTER)

            inputElement_select_address = wait.until(
                EC.element_to_be_clickable(
                    (By.ID, "WASTECOLLECTIONCALENDARV5_CALENDAR_ADDRESSLOOKUPADDRESS")
                )
            )
            dropdown_element = driver.find_element(
                By.ID, "WASTECOLLECTIONCALENDARV5_CALENDAR_ADDRESSLOOKUPADDRESS"
            )

            # Now create a Select object based on the found element
            dropdown = Select(dropdown_element)

            # Select the option by visible text
            dropdown.select_by_visible_text(house_number)

            results = wait.until(
                EC.element_to_be_clickable(
                    (By.CLASS_NAME, "bin-collection-dates-container")
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            # Extract data from the table
            bin_collection_data = []
            rows = soup.find(
                "table", class_="defaultgeneral bin-collection-dates"
            ).find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if cells:
                    date_str = cells[0].text.strip()
                    bin_type = cells[1].text.strip()
                    # Convert date string to the required format DD/MM/YYYY
                    date_obj = datetime.strptime(date_str, "%d %B %Y")
                    date_formatted = date_obj.strftime(date_format)
                    bin_collection_data.append(
                        {"collectionDate": date_formatted, "type": bin_type}
                    )

            # Convert to JSON
            json_data = {"bins": bin_collection_data}

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
