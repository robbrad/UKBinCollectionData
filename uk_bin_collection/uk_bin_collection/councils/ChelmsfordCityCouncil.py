import re
import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# This script pulls (in one hit) the data from Bromley Council Bins Data
import datetime
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
import time


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
            data = {"bins": []}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}

            uprn = kwargs.get("uprn")
            postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            driver = create_webdriver(web_driver, headless)
            url = kwargs.get("url")

            driver.execute_script(f"window.location.href='{url}'")

            wait = WebDriverWait(driver, 120)
            post_code_search = wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[@name="keyword"]'))
            )

            post_code_search.send_keys(postcode)

            submit_btn = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "__submitButton"))
            )

            submit_btn.send_keys(Keys.ENTER)

            address_results = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "directories-table"))
            )
            address_link = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//a[contains(text(), '{user_paon}')]")
                )
            )

            address_link.send_keys(Keys.ENTER)
            results = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "usercontent"))
            )

            # Make a BS4 object
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            # Get collection calendar
            calendar_urls = soup.find_all(
                "a", string=re.compile(r"view or download the collection calendar")
            )
            if len(calendar_urls) > 0:
                requests.packages.urllib3.disable_warnings()
                response = requests.get(calendar_urls[0].get("href"), headers=headers)

                # Make a BS4 object
                soup = BeautifulSoup(response.text, features="html.parser")
                soup.prettify()

                # Loop the months
                for month in soup.find_all("div", {"class": "usercontent"}):
                    year = ""
                    if month.find("h2") and "calendar" not in month.find("h2").get_text(
                        strip=True
                    ):
                        year = datetime.strptime(
                            month.find("h2").get_text(strip=True), "%B %Y"
                        ).strftime("%Y")
                    elif month.find("h3"):
                        year = datetime.strptime(
                            month.find("h3").get_text(strip=True), "%B %Y"
                        ).strftime("%Y")
                    if year != "":
                        for row in month.find_all("li"):
                            results = re.search(
                                "([A-Za-z]+ \\d\\d? [A-Za-z]+): (.+)",
                                row.get_text(strip=True),
                            )
                            if results:
                                dict_data = {
                                    "type": results.groups()[1].capitalize(),
                                    "collectionDate": datetime.strptime(
                                        results.groups()[0] + " " + year, "%A %d %B %Y"
                                    ).strftime(date_format),
                                }
                                data["bins"].append(dict_data)

                # Sort collections
                data["bins"].sort(
                    key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
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
