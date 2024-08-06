import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    This class is responsible for fetching and parsing bin collection data
    for Bolton Council using Selenium and BeautifulSoup.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            user_uprn = kwargs.get("uprn")
            check_uprn(user_uprn)

            user_postcode = kwargs.get("postcode")
            check_postcode(user_postcode)

            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            data = {"bins": []}

            page = "https://carehomes.bolton.gov.uk/bins.aspx"

            # Set up WebDriver with WebDriver Manager
            try:
                options = webdriver.ChromeOptions()
                if headless:
                    options.add_argument('--headless')  # Run headless if specified
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')

                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
                driver.get(page)
            except Exception as driver_error:
                print(f"Failed to create WebDriver: {driver_error}")
                raise

            # Wait for the webpage to load necessary elements
            wait = WebDriverWait(driver, 30)

            pc_search_box = wait.until(
                EC.presence_of_element_located((By.ID, "txtPostcode"))
            )
            pc_search_box.send_keys(user_postcode)

            pcsearch_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnSubmit")))
            pcsearch_btn.click()

            dropdown = wait.until(EC.element_to_be_clickable((By.ID, "ddlAddresses")))

            dropdown_options = wait.until(
                EC.presence_of_element_located((By.XPATH, "//select/option[1]"))
            )

            time.sleep(1)
            dropdownSelect = Select(dropdown)
            dropdownSelect.select_by_value(str(user_uprn))

            dropdown_options = wait.until(
                EC.presence_of_element_located((By.ID, "pnlStep3"))
            )

            # Parse the page source with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            collections = []

            # Find section with bins information
            sections = soup.find_all("div", {"class": "bin-info"})

            for item in sections:
                words = item.find_next("strong").text.split()[2:4]
                bin_type = " ".join(words).capitalize()

                date_list = item.find_all("p")
                for d in date_list:
                    clean_date_string = d.text.strip().lstrip("⯀").strip()

                    # Convert string to date
                    try:
                        next_collection = datetime.strptime(clean_date_string, "%A %d %B %Y")
                        collections.append((bin_type, next_collection))
                    except ValueError as ve:
                        print(f"Error parsing date '{clean_date_string}': {ve}")

            # Sort the collections by date
            ordered_data = sorted(collections, key=lambda x: x[1])

            # Compile the data into the required format
            for item in ordered_data:
                dict_data = {
                    "type": item[0],
                    "collectionDate": item[1].strftime(date_format),
                }
                data["bins"].append(dict_data)

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        return data


if __name__ == "__main__":
    # Example test inputs
    test_uprn = "100010934150"  # Replace with actual UPRN
    test_postcode = "BL1 7RH"   # Replace with actual postcode
    test_web_driver = "chrome"  # Ensure this driver is installed and configured
    test_headless = False  # Set to True for headless, False to see the browser actions

    council = CouncilClass()
    try:
        data = council.parse_data(
            page="", uprn=test_uprn, postcode=test_postcode, web_driver=test_web_driver, headless=test_headless
        )
        print("Final data output:", data)  # Debug statement
    except Exception as error:
        print("Exception during testing:", error)