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
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get("https://webapps.dacorum.gov.uk/bincollections/")

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "txtBxPCode"))
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "btnFindAddr"))
            )
            findAddress.click()

            # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//select[@id='lstBxAddrList']//option[contains(., '"
                        + user_paon
                        + "')]",
                    )
                )
            ).click()

            # Click search button
            findDates = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "MainContent_btnGetSchedules"))
            )
            findDates.click()

            # Wait for the collections table to appear
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "lblSelectedAddr"))
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            # Get collections div
            BinCollectionSchedule = soup.find("div", {"id": "MainContent_updPnl"})

            NextCollections = BinCollectionSchedule.find_all(
                "div", {"style": " margin:5px;"}
            )

            for Collection in NextCollections:
                strong_element = Collection.find("strong")
                if strong_element:
                    BinType = strong_element.text.strip()
                    # Skip if this is not a bin type (e.g., informational text)
                    if BinType and not any(skip_text in BinType.lower() for skip_text in 
                                         ["please note", "we may collect", "bank holiday", "different day"]):
                        date_cells = Collection.find_all("div", {"style": "display:table-cell;"})
                        if len(date_cells) > 1:
                            date_text = date_cells[1].get_text().strip()
                            if date_text:
                                try:
                                    CollectionDate = datetime.strptime(date_text, "%a, %d %b %Y")
                                    dict_data = {
                                        "type": BinType,
                                        "collectionDate": CollectionDate.strftime("%d/%m/%Y"),
                                    }
                                    # Check for duplicates before adding
                                    if dict_data not in data["bins"]:
                                        data["bins"].append(dict_data)
                                except ValueError:
                                    # Skip if date parsing fails
                                    continue

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
