from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys

import time
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)
        web_driver = kwargs.get("web_driver")
        headless= kwargs.get("headless")

        data = {"bins": []}

        # Get our initial session running
        page = "https://carehomes.bolton.gov.uk/bins.aspx"

        driver = create_webdriver(web_driver,headless)
        driver.get(page)

        # If you bang in the house number (or property name) and postcode in the box it should find your property
        wait = WebDriverWait(driver, 30)

        pc_search_box = wait.until(
            EC.presence_of_element_located((By.ID, "txtPostcode"))
        )

        pc_search_box.send_keys(user_postcode)

        pcsearch_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnSubmit")))

        pcsearch_btn.click()

        # Wait for the 'Select your property' dropdown to appear and select the first result
        dropdown = wait.until(EC.element_to_be_clickable((By.ID, "ddlAddresses")))

        dropdown_options = wait.until(
            EC.presence_of_element_located((By.XPATH, "//select/option[1]"))
        )
        time.sleep(1)
        # Create a 'Select' for it, then select the first address in the list
        # (Index 0 is "Make a selection from the list")
        dropdownSelect = Select(dropdown)
        dropdownSelect.select_by_value(str(user_uprn))
        dropdown_options = wait.until(
            EC.presence_of_element_located((By.ID, "pnlStep3"))
        )

        soup = BeautifulSoup(driver.page_source, features="html.parser")
        soup.prettify()

        collections = []

        # Find section with bins in
        sections = soup.find_all("div", {"class": "bin-info"})

        # For each bin section, get the text and the list elements
        for item in sections:
            words = item.find_next("strong").text.split()[2:4]
            bin_type = " ".join(words).capitalize()
            date_list = item.find_all("p")
            for d in date_list:
                next_collection = datetime.strptime(d.text.strip(), "%A %d %B %Y")
                collections.append((bin_type, next_collection))

        # Sort the text and list elements by date
        ordered_data = sorted(collections, key=lambda x: x[1])

        # Put the elements into the dictionary
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
