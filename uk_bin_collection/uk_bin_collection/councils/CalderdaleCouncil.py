# This script pulls (in one hit) the data from Bromley Council Bins Data
import datetime
import time
from datetime import datetime

import requests
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
            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            check_uprn(user_uprn)
            check_postcode(user_postcode)

            bin_data_dict = {"bins": []}
            collections = []
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            data = {"bins": []}

            # Get our initial session running
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(kwargs.get("url"))

            wait = WebDriverWait(driver, 30)
            postcode = wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="pPostcode"]'))
            )

            postcode.send_keys(user_postcode)
            postcode_search_btn = wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "searchbox_submit"))
            )
            postcode_search_btn.send_keys(Keys.ENTER)
            # Wait for the 'Select your property' dropdown to appear and select the first result
            dropdown = wait.until(EC.element_to_be_clickable((By.ID, "uprn")))

            # Create a 'Select' for it, then select the first address in the list
            # (Index 0 is "Make a selection from the list")
            dropdownSelect = Select(dropdown)
            dropdownSelect.select_by_value(str(user_uprn))
            checkbox = wait.until(EC.presence_of_element_located((By.ID, "gdprTerms")))
            checkbox.send_keys(Keys.SPACE)
            get_bin_data_btn = wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "searchbox_submit"))
            )
            get_bin_data_btn.send_keys(Keys.ENTER)
            # Make a BS4 object
            results = wait.until(EC.presence_of_element_located((By.ID, "collection")))
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            data = {"bins": []}

            # Get collections
            row_index = 0
            for row in soup.find("table", {"id": "collection"}).find_all("tr"):
                # Skip headers row
                if row_index < 1:
                    row_index += 1
                    continue
                else:
                    # Get bin info
                    bin_info = row.find_all("td")
                    # Get the bin type
                    bin_type = bin_info[0].find("strong").get_text(strip=True)
                    # Get the collection date
                    collection_date = ""
                    for p in bin_info[2].find_all("p"):
                        if "your next collection" in p.get_text(strip=True):
                            collection_date = datetime.strptime(
                                " ".join(
                                    p.get_text(strip=True)
                                    .replace("will be your next collection.", "")
                                    .split()
                                ),
                                "%A %d %B %Y",
                            )

                    if collection_date != "":
                        # Append the bin type and date to the data dict
                        dict_data = {
                            "type": bin_type,
                            "collectionDate": collection_date.strftime(date_format),
                        }
                        data["bins"].append(dict_data)

                    row_index += 1

            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
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
