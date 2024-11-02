from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

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
        driver = None
        try:
            data = {"bins": []}
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(
                "https://www.sthelens.gov.uk/article/3473/Check-your-collection-dates"
            )

            """
            accept_button = WebDriverWait(driver, timeout=30).until(
                EC.element_to_be_clickable((By.ID, "ccc-notify-accept"))
            )
            accept_button.click()
            """

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.ID, "RESIDENTCOLLECTIONDATES_PAGE1_POSTCODE")
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "RESIDENTCOLLECTIONDATES_PAGE1_FINDADDRESS_NEXT")
                )
            )
            findAddress.click()

            WebDriverWait(driver, timeout=30).until(
                EC.element_to_be_clickable(
                    (By.ID, "RESIDENTCOLLECTIONDATES_PAGE1_ADDRESS_chosen")
                )
            ).click()

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f"//ul[@id='RESIDENTCOLLECTIONDATES_PAGE1_ADDRESS-chosen-search-results']/li[starts-with(text(), '{user_paon}')]",
                    )
                )
            ).click()

            WebDriverWait(driver, timeout=30).until(
                EC.element_to_be_clickable(
                    (By.ID, "RESIDENTCOLLECTIONDATES_PAGE1_ADDRESSNEXT_NEXT")
                )
            ).click()

            # Wait for the collections table to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "RESIDENTCOLLECTIONDATES__FIELDS_OUTER")
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Get the month rows first
            current_month = ""
            for row in soup.find_all("tr"):
                # Check if the row is a month header (contains 'th' tag)
                if row.find("th"):
                    current_month = row.find("th").get_text(strip=True)
                else:
                    # Extract the date, day, and waste types
                    columns = row.find_all("td")
                    if len(columns) >= 4:
                        day = columns[0].get_text(strip=True)
                        date = day + " " + current_month
                        waste_types = columns[3].get_text(strip=True)

                        for type in waste_types.split(" & "):
                            dict_data = {
                                "type": type,
                                "collectionDate": datetime.strptime(
                                    date,
                                    "%d %B %Y",
                                ).strftime("%d/%m/%Y"),
                            }
                            data["bins"].append(dict_data)

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
