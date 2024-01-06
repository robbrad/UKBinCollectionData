from datetime import datetime
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys

import pandas as pd
import urllib.request


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        web_driver = kwargs.get("web_driver")
        headless= kwargs.get("headless")

        # Create Selenium webdriver
        page = f"https://www.eastriding.gov.uk/environment/bins-rubbish-recycling/bins-and-collections/bin-collection-dates/"

        driver = create_webdriver(web_driver,headless)
        driver.get(page)

        wait = WebDriverWait(driver, 60)

        try:
            accept_cookies = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="er-cookie-placeholder-settings"]/div/a[1]')
                )
            )

            accept_cookies.click()
        except:
            print(
                "Cookies acceptance element not found or clickable within the specified time."
            )
            pass

        expand_postcode_box = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[@href='#when-and-where-should-i-put-my-bin-out']")
            )
        )

        expand_postcode_box.click()

        postcode_box = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//input[@placeholder='Enter your postcode']")
            )
        )
        postcode_box.send_keys(user_postcode)

        postcode_search_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Search']"))
        )
        postcode_search_btn.send_keys(Keys.ENTER)

        dropdown = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//div[@class='er-select-wrapper']/select[@class='dropdown']",
                )
            )
        )

        options_present = wait.until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "select.dropdown option")
            )
        )
        drop = Select(dropdown)
        drop.select_by_visible_text(str(user_paon))

        results_present = wait.until(
            EC.presence_of_element_located(
                (
                    By.CLASS_NAME,
                    "results",
                )
            )
        )

        data = {"bins": []}  # dictionary for data
        soup = BeautifulSoup(driver.page_source, "html.parser")

        bin_types = {}  # Dictionary to store bin types

        # Extract bin types from header elements
        header_elements = soup.find_all(
            "li", class_=lambda x: x and x.startswith("header")
        )
        for header_element in header_elements:
            bin_type = header_element.get_text(strip=True)
            bin_class = [cls for cls in header_element.get("class") if cls != "header"]
            if bin_class:
                bin_types[bin_class[0]] = bin_type

        # Extract collection dates and associate them with respective bin types
        date_elements = soup.find_all("li", class_=lambda x: x and x.startswith("date"))
        for date_element in date_elements:
            bin_class = [cls for cls in date_element.get("class") if cls != "date"]
            if bin_class:
                bin_type = bin_types.get(bin_class[0])
                span_text = date_element.find("span").get_text(strip=True)
                collection_date = datetime.strptime(span_text, "%a, %d %b %Y")
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )

        return data
