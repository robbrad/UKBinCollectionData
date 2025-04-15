import urllib.request
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            """
            Parse council provided CSVs to get the latest bin collections for address
            """

            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_uprn(user_uprn)
            check_postcode(user_postcode)
            # Create Selenium webdriver
            page = f"https://www.leeds.gov.uk/residents/bins-and-recycling/check-your-bin-day"

            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            wait = WebDriverWait(driver, 60)
            postcode_box = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//input[@id='postcode']",
                    )
                )
            )
            postcode_box.send_keys(user_postcode)
            postcode_btn_present = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//button[contains(text(),'Look up Address')]",
                    )
                )
            )
            postcode_btn_present.click()

            dropdown_present = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        '//option[contains(text(),"Select an address")]/parent::select',
                    )
                )
            )

            dropdown_select = Select(dropdown_present)

            dropdown_select.select_by_value(user_uprn)

            result = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//div[@class='lcc-bins']",
                    )
                )
            )

            data = {"bins": []}  # dictionary for data
            soup = BeautifulSoup(
                result.get_attribute("innerHTML"), features="html.parser"
            )

            bin_sections = soup.select("div.lcc-bin:not(.lcc-bin--calendar)")

            for section in bin_sections:
                h3_text = section.find("h3").get_text(strip=True)
                bin_type = h3_text.split()[0]  # e.g., 'Black', 'Brown', 'Green'

                # Find all <li> elements inside the bin days list
                date_elements = section.select("div.lcc-bin__days li")
                for li in date_elements:
                    raw_date = li.get_text(strip=True)
                    if not raw_date:
                        continue
                    try:
                        formatted_date = datetime.strptime(
                            raw_date, "%A %d %b %Y"
                        ).strftime(date_format)
                        data["bins"].append(
                            {"type": bin_type, "collectionDate": formatted_date}
                        )
                    except ValueError:
                        print(f"Skipping unparseable date: {raw_date}")
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
