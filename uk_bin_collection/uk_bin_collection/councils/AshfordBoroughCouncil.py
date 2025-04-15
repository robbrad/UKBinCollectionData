from datetime import datetime

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            # Get and check UPRN
            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            check_uprn(user_uprn)
            check_postcode(user_postcode)
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            bindata = {"bins": []}

            API_URL = "https://secure.ashford.gov.uk/waste/collectiondaylookup/"

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(API_URL)

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.ID, "ContentPlaceHolder1_CollectionDayLookup2_TextBox_PostCode")
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.ID,
                        "ContentPlaceHolder1_CollectionDayLookup2_Button_PostCodeSearch",
                    )
                )
            )
            findAddress.click()

            # Wait for the 'Select your property' dropdown to appear and select the first result
            dropdown = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.ID,
                        "ContentPlaceHolder1_CollectionDayLookup2_DropDownList_Addresses",
                    )
                )
            )

            # Create a 'Select' for it, then select the first address in the list
            # (Index 0 is "Make a selection from the list")
            dropdownSelect = Select(dropdown)
            dropdownSelect.select_by_value(str(user_uprn))

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.ID,
                        "ContentPlaceHolder1_CollectionDayLookup2_Button_SelectAddress",
                    )
                )
            )
            findAddress.click()

            h4_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h4[contains(text(), 'Collection Dates')]")
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            bin_tables = soup.find_all("table")

            for bin_table in bin_tables:
                bin_text = bin_table.find(
                    "td", id=re.compile("CollectionDayLookup2_td_")
                )
                if not bin_text:
                    continue

                bin_type_soup = bin_text.find("b")

                if not bin_type_soup:
                    continue
                bin_type: str = bin_type_soup.text.strip().split(" (")[0]

                date_soup = bin_text.find(
                    "span", id=re.compile(r"CollectionDayLookup2_Label_\w*_Date")
                )
                if not date_soup or (
                    " " not in date_soup.text.strip()
                    and date_soup.text.strip().lower() != "today"
                ):
                    continue
                date_str: str = date_soup.text.strip()
                try:
                    if date_soup.text.strip().lower() == "today":
                        date = datetime.now().date()
                    else:
                        date = datetime.strptime(
                            date_str.split(" ")[1], "%d/%m/%Y"
                        ).date()

                except ValueError:
                    continue

                dict_data = {
                    "type": bin_type,
                    "collectionDate": date.strftime("%d/%m/%Y"),
                }
                bindata["bins"].append(dict_data)

        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return bindata
