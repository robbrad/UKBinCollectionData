from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
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
            url = kwargs.get("url")
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get("https://www.renfrewshire.gov.uk/bin-day")

            accept_button = WebDriverWait(driver, timeout=30).until(
                EC.element_to_be_clickable((By.ID, "ccc-notify-accept"))
            )
            accept_button.click()

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.ID, "RENFREWSHIREBINCOLLECTIONS_PAGE1_ADDRESSLOOKUPPOSTCODE")
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "RENFREWSHIREBINCOLLECTIONS_PAGE1_ADDRESSLOOKUPSEARCH")
                )
            )
            findAddress.click()

            # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//select[@id='RENFREWSHIREBINCOLLECTIONS_PAGE1_ADDRESSLOOKUPADDRESS']//option[contains(., '"
                        + user_paon
                        + "')]",
                    )
                )
            ).click()

            # Wait for the collections table to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "RENFREWSHIREBINCOLLECTIONS_PAGE1_COLLECTIONDETAILS")
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            next_collection_div = soup.find(
                "div", {"class": "collection collection--next"}
            )

            next_collection_date = datetime.strptime(
                next_collection_div.find("p", {"class": "collection__date"})
                .get_text()
                .strip(),
                "%A %d %B %Y",
            )

            next_collection_bin = next_collection_div.findAll(
                "p", {"class": "bins__name"}
            )

            for row in next_collection_bin:
                dict_data = {
                    "type": row.get_text().strip(),
                    "collectionDate": next_collection_date.strftime("%d/%m/%Y"),
                }
                data["bins"].append(dict_data)

            future_collection_div = soup.find(
                "div", {"class": "collection collection--future"}
            )

            future_collection_row = future_collection_div.findAll(
                "div", {"class": "collection__row"}
            )

            for collection_row in future_collection_row:
                future_collection_date = datetime.strptime(
                    collection_row.find("p", {"class": "collection__date"})
                    .get_text()
                    .strip(),
                    "%A %d %B %Y",
                )
                future_collection_bin = collection_row.findAll(
                    "p", {"class": "bins__name"}
                )

                for row in future_collection_bin:
                    dict_data = {
                        "type": row.get_text().strip(),
                        "collectionDate": future_collection_date.strftime("%d/%m/%Y"),
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
