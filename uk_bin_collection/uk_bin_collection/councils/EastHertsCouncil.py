from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Get and check UPRN
        driver = None
        try:
            user_postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")
            check_paon(user_paon)
            check_postcode(user_postcode)
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            bindata = {"bins": []}

            API_URL = "https://uhte-wrp.whitespacews.com"

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(API_URL)

            # Click Find my bin collection day button
            collectionButton = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Find my bin collection day"))
            )
            collectionButton.click()

            main_content = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "main-content"))
            )

            # Wait for the property number field to appear then populate it
            inputElement_number = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.ID,
                        "address_name_number",
                    )
                )
            )
            inputElement_number.send_keys(user_paon)

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.ID,
                        "address_postcode",
                    )
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            continueButton = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.ID,
                        "Submit",
                    )
                )
            )
            continueButton.click()

            # Wait for the 'Search Results' to appear and select the first result
            property = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "li.app-subnav__section-item a",
                        # "app-subnav__link govuk-link clicker colordarkblue fontfamilyArial fontsize12rem",
                        # "//a[starts-with(@aria-label, '{user_paon}')]",
                    )
                )
            )
            property.click()

            upcoming_scheduled_collections = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "upcoming-scheduled-collections")
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            collections = []
            for collection in soup.find_all(
                "u1",
                class_="displayinlineblock justifycontentleft alignitemscenter margin0 padding0",
            ):
                date = collection.find(
                    "p", string=lambda text: text and "/" in text
                ).text.strip()  # Extract date
                service = collection.find(
                    "p", string=lambda text: text and "Collection Service" in text
                ).text.strip()  # Extract service type
                collections.append({"date": date, "service": service})

            # Print the parsed data
            for item in collections:

                dict_data = {
                    "type": item["service"],
                    "collectionDate": item["date"],
                }
                bindata["bins"].append(dict_data)

        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return bindata
