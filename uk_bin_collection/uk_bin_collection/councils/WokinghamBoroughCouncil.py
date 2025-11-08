from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
            source_date_format = "%d/%m/%Y"
            timeout = 10
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(
                "https://www.wokingham.gov.uk/rubbish-and-recycling/waste-collection/find-your-bin-collection-day"
            )

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.ID, "edit-postcode-search-csv"))
            )
            inputElement_postcode.send_keys(user_postcode)

            # Simulates hitting the "Enter" key to submit
            inputElement_postcode.send_keys(Keys.RETURN)

            # Select the exact address from the drop down box
            WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        ""
                        "//*[@id='edit-address-options-csv']//option[starts-with(normalize-space(.), '"
                        + user_paon
                        + "')]",
                    )
                )
            ).click()

            # Wait for the Show collection dates button to appear, then click it to get the collection dates
            inputElement_show_dates_button = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="edit-show-collection-dates-csv"]')
                )
            )
            inputElement_show_dates_button.send_keys(Keys.RETURN)

            # Wait for the collection dates elements to load
            collection_date_cards = WebDriverWait(driver, timeout).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, '//div[@class = "card card--waste card--blue-light"]')
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            collection_cards = soup.find_all(
                "div", {"class": "card card--waste card--blue-light"}
            )

            for collection_card in collection_cards:
                collection_date_cards = collection_card.find_all(
                    "div", {"class": "card__content"}
                )

                for collection_date_card in collection_date_cards:

                    waste_type = collection_date_card.find(
                        "h3", {"class": "heading heading--sub heading--tiny"}
                    )

                    collection_date = collection_date_card.find(
                        "span", {"class": "card__date"}
                    )

                    dt_collection_date = datetime.strptime(
                        collection_date.text.strip().split(" ")[1], source_date_format
                    )
                    dict_data = {
                        "type": waste_type.text.strip().split("(")[0].strip(),
                        "collectionDate": dt_collection_date.strftime(date_format),
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
