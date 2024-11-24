import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

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

        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        web_driver = kwargs.get("web_driver")
        headless = kwargs.get("headless")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        # Initialize the WebDriver (Chrome in this case)
        driver = create_webdriver(
            web_driver,
            headless,
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            __name__,
        )

        # Step 1: Navigate to the form page
        driver.get(
            "https://lewisham.gov.uk/myservices/recycling-and-rubbish/your-bins/collection"
        )

        try:
            cookie_accept_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
                )
            )
            cookie_accept_button.click()
        except Exception:
            print("No cookie consent banner found or already dismissed.")

        # Wait for the form to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "address-finder"))
        )

        # Step 2: Locate the input field for the postcode
        postcode_input = driver.find_element(By.CLASS_NAME, "js-address-finder-input")

        # Enter the postcode
        postcode_input.send_keys(user_postcode)  # Replace with your desired postcode
        time.sleep(1)  # Optional: Wait for the UI to react

        # Step 4: Click the "Find address" button with retry logic
        find_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.CLASS_NAME, "js-address-finder-step-address")
            )
        )
        find_button.click()

        # Wait for the address selector to appear and options to load
        WebDriverWait(driver, 10).until(
            lambda d: len(
                d.find_element(By.ID, "address-selector").find_elements(
                    By.TAG_NAME, "option"
                )
            )
            > 1
        )

        # Select the dropdown and print available options
        address_selector = driver.find_element(By.ID, "address-selector")

        # Use Select class to interact with the dropdown
        select = Select(address_selector)
        if len(select.options) > 1:
            select.select_by_value(user_uprn)
        else:
            print("No additional addresses available to select")

        # Wait until the URL contains the expected substring
        WebDriverWait(driver, 10).until(
            EC.url_contains("/find-your-collection-day-result")
        )

        # Parse the HTML
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Extract the main container
        collection_result = soup.find("div", class_="js-find-collection-result")

        # Extract each collection type and its frequency/day
        for strong_tag in collection_result.find_all("strong"):
            bin_type = strong_tag.text.strip()  # e.g., "Food waste"
            # Extract day from the sibling text
            schedule_text = (
                strong_tag.next_sibling.next_sibling.next_sibling.text.strip()
                .split("on\n")[-1]
                .replace("\n", "")
                .replace("\t", "")
            )
            day = schedule_text.strip().split(".")[0]

            # Extract the next collection date
            if "Your next collection date is" in schedule_text:
                start_index = schedule_text.index("Your next collection date is") + len(
                    "Your next collection date is"
                )
                next_collection_date = (
                    schedule_text[start_index:].strip().split("\n")[0].strip()
                )
            else:
                next_collection_date = get_next_day_of_week(day, date_format)

            dict_data = {
                "type": bin_type,
                "collectionDate": next_collection_date,
            }
            bindata["bins"].append(dict_data)

        return bindata
