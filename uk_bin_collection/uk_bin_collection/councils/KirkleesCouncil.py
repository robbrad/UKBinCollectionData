import time
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.drivers.chrome import ChromeDriver

from selenium import webdriver

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
        data = {"bins": []}
        collections = []

        user_paon = kwargs["paon"]
        user_postcode = kwargs["postcode"]

        self._driver = driver = webdriver.Chrome()
        # self._driver = driver = create_webdriver(
        #     web_driver=kwargs["web_driver"],
        #     headless=kwargs.get("headless", True),
        #     session_name=__name__,
        # )
        driver.implicitly_wait(1)

        driver.get(
            "https://my.kirklees.gov.uk/service/Bins_and_recycling___Manage_your_bins"
        )

        time.sleep(5)

        # Switch to iframe
        iframe = driver.find_element(By.CSS_SELECTOR, "#fillform-frame-1")
        driver.switch_to.frame(iframe)

        wait_for_element(
            driver, By.ID, "mandatory_Postcode", timeout=10
        )

        postcode_input = driver.find_element(
            By.ID, "Postcode"
        )
        postcode_input.send_keys(user_postcode)

        wait_for_element(driver, By.ID, "List")
        time.sleep(2)

        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//select[@name='List']//option[contains(., '"
                    + user_paon
                    + "')]",
                )
            )
        ).click()

        time.sleep(10)

        # For whatever reason, the page sometimes automatically goes to the next step
        next_button = driver.find_element(By.XPATH, '/html/body/div/div/section/form/div/nav/div[2]/button')
        if next_button.is_displayed():
            next_button.click()


        time.sleep(5)

        soup = BeautifulSoup(self._driver.page_source, features="html.parser")
        soup.prettify()

        radio_button_text = soup.find_all("label", {"class": "radio-label"})
        for label in radio_button_text:
            parsed_text = label.text.split("x ")
            row = parsed_text[1].lower().split("collection date: ")
            bin_type = row[0].split("(")[0].strip()
            date_text = row[1].strip().replace(")", "")
            if date_text == "today":
                bin_date = datetime.now()
            else:
                bin_date = datetime.strptime(date_text, "%A %d %B %Y")
            collections.append((bin_type, bin_date))

        ordered_data = sorted(collections, key=lambda x: x[1])
        for item in ordered_data:
            dict_data = {
                "type": item[0].replace("standard ", "").capitalize(),
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
