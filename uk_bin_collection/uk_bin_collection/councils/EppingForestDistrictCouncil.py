from datetime import datetime

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.common import date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        postcode = kwargs.get("postcode", "")
        web_driver = kwargs.get("web_driver")
        headless = kwargs.get("headless")
        data = {"bins": []}

        try:
            # Initialize webdriver with logging
            print(f"Initializing webdriver with: {web_driver}, headless: {headless}")
            driver = create_webdriver(web_driver, headless, None, __name__)

            # Format and load URL
            page_url = f"https://eppingforestdc.maps.arcgis.com/apps/instant/lookup/index.html?appid=bfca32b46e2a47cd9c0a84f2d8cdde17&find={postcode}"
            print(f"Accessing URL: {page_url}")
            driver.get(page_url)

            # Wait for initial page load
            wait = WebDriverWait(driver, 20)  # Reduced timeout to fail faster if issues

            # First wait for any loading indicators to disappear
            try:
                print("Waiting for loading spinner to disappear...")
                wait.until(
                    EC.invisibility_of_element_located(
                        (By.CSS_SELECTOR, ".esri-widget--loader-container")
                    )
                )
            except Exception as e:
                print(f"Loading spinner wait failed (may be normal): {str(e)}")

            # Then wait for the content container
            print("Waiting for content container...")
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".esri-feature-content")
                )
            )

            # Finally wait for actual content
            print("Waiting for content to be visible...")
            content = wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, ".esri-feature-content")
                )
            )

            # Check if content is actually present
            if not content:
                raise ValueError("Content element found but empty")

            print("Content found, getting page source...")
            html_content = driver.page_source

            soup = BeautifulSoup(html_content, "html.parser")
            bin_info_divs = soup.select(".esri-feature-content p")
            for div in bin_info_divs:
                if "collection day is" in div.text:
                    bin_type, date_str = div.text.split(" collection day is ")
                    bin_dates = datetime.strptime(
                        date_str.strip(), "%d/%m/%Y"
                    ).strftime(date_format)
                    data["bins"].append(
                        {"type": bin_type.strip(), "collectionDate": bin_dates}
                    )

            return data
        finally:
            driver.quit()
