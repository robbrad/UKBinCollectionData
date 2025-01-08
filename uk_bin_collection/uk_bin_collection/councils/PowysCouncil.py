import time

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from selenium.webdriver.common.by import By
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
        data = {"bins": []}
        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        web_driver = kwargs.get("web_driver")
        headless = kwargs.get("headless")
        check_paon(user_paon)
        check_postcode(user_postcode)

        user_paon = user_paon.upper()

        # Create Selenium webdriver
        driver = create_webdriver(web_driver, headless, None, __name__)
        driver.get("https://en.powys.gov.uk/binday")

        accept_button = WebDriverWait(driver, timeout=10).until(
            EC.element_to_be_clickable(
                (
                    By.NAME,
                    "acceptall",
                )
            )
        )
        accept_button.click()

        # Wait for the postcode field to appear then populate it
        inputElement_postcode = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, "BINDAYLOOKUP_ADDRESSLOOKUP_ADDRESSLOOKUPPOSTCODE")
            )
        )
        inputElement_postcode.send_keys(user_postcode)

        # Click search button
        findAddress = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, "BINDAYLOOKUP_ADDRESSLOOKUP_ADDRESSLOOKUPSEARCH")
            )
        )
        findAddress.click()

        # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//select[@id='BINDAYLOOKUP_ADDRESSLOOKUP_ADDRESSLOOKUPADDRESS']//option[contains(., '"
                    + user_paon
                    + "')]",
                )
            )
        ).click()

        # Wait for the submit button to appear, then click it to get the collection dates
        WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable(
                (By.ID, "BINDAYLOOKUP_ADDRESSLOOKUP_ADDRESSLOOKUPBUTTONS_NEXT")
            )
        ).click()

        # Wait for the collections table to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, "BINDAYLOOKUP_COLLECTIONDATES_COLLECTIONDATES")
            )
        )

        soup = BeautifulSoup(driver.page_source, features="html.parser")

        # General rubbish collection dates
        general_rubbish_section = soup.find(
            "h3", string="General Rubbish / Wheelie bin"
        )
        general_rubbish_dates = [
            li.text for li in general_rubbish_section.find_next("ul").find_all("li")
        ]

        for date in general_rubbish_dates:
            dict_data = {
                "type": "General Rubbish / Wheelie bin",
                "collectionDate": datetime.strptime(
                    remove_ordinal_indicator_from_date_string(date), "%d %B %Y"
                ).strftime(date_format),
            }
            data["bins"].append(dict_data)

        # Recycling and food waste collection dates
        recycling_section = soup.find("h3", string="Recycling and Food Waste")
        recycling_dates = [
            li.text for li in recycling_section.find_next("ul").find_all("li")
        ]

        for date in recycling_dates:
            dict_data = {
                "type": "Recycling and Food Waste",
                "collectionDate": datetime.strptime(
                    remove_ordinal_indicator_from_date_string(date), "%d %B %Y"
                ).strftime(date_format),
            }
            data["bins"].append(dict_data)

        # Garden waste collection dates
        garden_waste_section = soup.find("h3", string="Garden Waste")
        garden_waste_dates = [
            li.text for li in garden_waste_section.find_next("ul").find_all("li")
        ]
        for date in garden_waste_dates:
            try:
                dict_data = {
                    "type": "Garden Waste",
                    "collectionDate": datetime.strptime(
                        remove_ordinal_indicator_from_date_string(date), "%d %B %Y"
                    ).strftime(date_format),
                }
                data["bins"].append(dict_data)
            except:
                continue

        return data
