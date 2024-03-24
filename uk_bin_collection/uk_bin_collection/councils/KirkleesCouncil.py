from datetime import datetime
from typing import Optional

from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import create_webdriver
from uk_bin_collection.uk_bin_collection.common import date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def wait_for_element(driver, element_type, element: str, timeout: int = 5):
    element_present = EC.presence_of_element_located((element_type, element))
    wait_for_element_conditions(driver, element_present, timeout=timeout)


def wait_for_element_conditions(driver, conditions, timeout: int = 5):
    try:
        WebDriverWait(driver, timeout).until(conditions)
    except TimeoutException:
        print("Timed out waiting for page to load")
        raise


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def __init__(self):
        self._driver: Optional[WebDriver] = None

    def parse_data(self, *args, **kwargs) -> dict:
        try:
            return self._parse_data(*args, **kwargs)
        finally:
            if self._driver:
                self._driver.quit()

    def _parse_data(self, page: str, **kwargs) -> dict:
        """
        Process:

        - Use a house number and postcode that is known to be domestic and resolves to a
          single unique address. When the address search form is submitted with
          those details, a session is created

        - Now a session exists, navigate to the calendar URL, specifying the UPRN

        - Extract info from the 'alt' attribute of the images on that page
        """
        bins = []

        user_paon = kwargs["paon"]
        user_postcode = kwargs["postcode"]

        self._driver = driver = create_webdriver(
            web_driver=kwargs["web_driver"], headless=kwargs.get("headless", True)
        )
        driver.implicitly_wait(1)

        driver.get(
            "https://www.kirklees.gov.uk/beta/your-property-bins-recycling/your-bins/default.aspx"
        )

        wait_for_element(
            driver, By.ID, "cphPageBody_cphContent_thisGeoSearch_txtGeoPremises"
        )

        house_input = driver.find_element(
            By.ID, "cphPageBody_cphContent_thisGeoSearch_txtGeoPremises"
        )
        house_input.send_keys(user_paon)

        postcode_input = driver.find_element(
            By.ID, "cphPageBody_cphContent_thisGeoSearch_txtGeoSearch"
        )
        postcode_input.send_keys(user_postcode)

        # submit address search
        driver.find_element(By.ID, "butGeoSearch").send_keys(Keys.RETURN)

        wait_for_element(
            driver,
            By.ID,
            "cphPageBody_cphContent_wtcDomestic240__lnkAccordionAnchor",
            # submitting can be slow
            timeout=30
        )

        # Open the panel
        driver.find_element(
            By.ID, "cphPageBody_cphContent_wtcDomestic240__lnkAccordionAnchor"
        ).click()

        # Domestic waste calendar
        wait_for_element(
            driver, By.ID, "cphPageBody_cphContent_wtcDomestic240__LnkCalendar"
        )
        calendar_link = driver.find_element(
            By.ID, "cphPageBody_cphContent_wtcDomestic240__LnkCalendar"
        )
        driver.execute_script("arguments[0].click();", calendar_link)

        # <img alt="Recycling                      collection date 14 March 2024"
        # <img alt="Domestic                       collection date 21 March 2024
        date_strings = driver.find_elements(
            By.CSS_SELECTOR, 'img[alt*="collection date"]'
        )

        for date in date_strings:
            bin_type, _, _, day, month, year = date.get_attribute("alt").split()
            collection_date = datetime.strptime(
                f"{day} {month} {year}", "%d %B %Y"
            ).strftime(date_format)

            bins.append(
                {
                    "type": bin_type,
                    "collectionDate": collection_date,
                }
            )

        return {"bins": bins}
