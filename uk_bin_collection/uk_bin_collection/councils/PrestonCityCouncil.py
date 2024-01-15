from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from selenium.webdriver.common.keys import Keys


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
            page = "https://selfservice.preston.gov.uk/service/Forms/FindMyNearest.aspx?Service=bins"

            data = {"bins": []}

            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless)
            driver.get(page)

            # If you bang in the house number (or property name) and postcode in the box it should find your property
            inputElement_address = driver.find_element(
                By.ID,
                "MainContent_txtAddress",
            )

            inputElement_address.send_keys(user_paon)
            inputElement_address.send_keys(" ")
            inputElement_address.send_keys(user_postcode)

            driver.find_element(
                By.ID,
                "btnSearch",
            ).send_keys(Keys.ENTER)

            # Wait for the 'Select your property' dropdown to appear and select the first result
            dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "MainContent_ddlSearchResults"))
            )
            # Create a 'Select' for it, then select the first address in the list
            # (Index 0 is "Make a selection from the list")
            dropdownSelect = Select(dropdown)
            dropdownSelect.select_by_index(1)

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            topLevelSpan = soup.find("span", id="MainContent_lblMoreCollectionDates")

            collectionDivs = topLevelSpan.find_all("div", {"id": "container"})

            for collectionDiv in collectionDivs:
                type_and_date_divs = collectionDiv.find_all("b")
                bin_type = type_and_date_divs[0].text

                date_elements = collectionDiv.find_all("li")
                for date_element in date_elements:
                    date_string = date_element.find("span").text.split(" ")[1]
                    collection_date = datetime.strptime(
                        date_string, "%d/%m/%Y"
                    ).strftime(date_format)

                    data["bins"].append(
                        {
                            "type": re.sub(r"[^a-zA-Z0-9,\s]", "", bin_type).strip(),
                            "collectionDate": collection_date,
                        }
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
