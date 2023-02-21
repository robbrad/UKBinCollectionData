import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def get_data(self, df) -> dict:
        # Create dictionary of data to be returned
        data = {"bins": []}

        # Output collection data into dictionary
        for i, row in df.iterrows():
            dict_data = {
                "type": row["Collection Name"],
                "collectionDate": row["Next Collection Due"],
            }

            data["bins"].append(dict_data)

        return data

    def parse_data(self, page: str, **kwargs) -> dict:
        page = "https://chiltern.gov.uk/collection-dates"

        # Assign user info
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")

        # Set up Selenium to run 'headless'
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # Create Selenium webdriver
        driver = webdriver.Chrome(options=options)
        driver.get(page)

        # Enter postcode in text box and wait
        inputElement_pc = driver.find_element(
            By.ID, "COPYOFECHOCOLLECTIONDATES_ADDRESSSELECTION_ADDRESSSELECTIONPOSTCODE"
        )
        inputElement_pc.send_keys(user_postcode)
        inputElement_pc.send_keys(Keys.ENTER)

        time.sleep(4)

        # Select address from dropdown and wait
        inputElement_ad = Select(
            driver.find_element(
                By.ID,
                "COPYOFECHOCOLLECTIONDATES_ADDRESSSELECTION_ADDRESSSELECTIONADDRESS",
            )
        )

        inputElement_ad.select_by_visible_text(user_paon)

        time.sleep(4)

        # Submit address information and wait
        inputElement_bn = driver.find_element(
            By.ID, "COPYOFECHOCOLLECTIONDATES_ADDRESSSELECTION_NAV1_NEXT"
        ).click()

        time.sleep(4)

        # Read next collection information into Pandas
        table = driver.find_element(
            By.ID, "COPYOFECHOCOLLECTIONDATES_PAGE1_DATES2"
        ).get_attribute("outerHTML")
        df = pd.read_html(table, header=[1])
        df = df[0]

        # Parse data into dict
        data = self.get_data(df)

        return data
