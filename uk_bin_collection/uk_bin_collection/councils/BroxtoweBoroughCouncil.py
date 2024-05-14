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
            page = "https://selfservice.broxtowe.gov.uk/renderform.aspx?t=217&k=9D2EF214E144EE796430597FB475C3892C43C528"

            data = {"bins": []}

            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_uprn(user_uprn)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless)
            driver.get(page)

            # Populate postcode field
            inputElement_postcode = driver.find_element(
                By.ID,
                "ctl00_ContentPlaceHolder1_FF5683TB",
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            driver.find_element(
                By.ID,
                "ctl00_ContentPlaceHolder1_FF5683BTN",
            ).click()

            # Wait for the 'Select address' dropdown to appear and select option matching UPRN
            dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "ctl00_ContentPlaceHolder1_FF5683DDL")
                )
            )
            # Create a 'Select' for it, then select the matching URPN option
            dropdownSelect = Select(dropdown)
            dropdownSelect.select_by_value("U" + user_uprn)

            # Wait for the submit button to appear, then click it to get the collection dates
            submit = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "ctl00_ContentPlaceHolder1_btnSubmit")
                )
            )
            submit.click()

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            bins_div = soup.find("div", id="ctl00_ContentPlaceHolder1_FF5686FormGroup")
            if bins_div:
                bins_table = bins_div.find("table")
                if bins_table:
                    # Get table rows
                    for row in bins_table.find_all("tr"):
                        # Get the rows cells
                        cells = row.find_all("td")
                        bin_type = cells[0].get_text(strip=True)
                        # Skip header row
                        if bin_type and cells[3] and bin_type != "Bin Type":
                            if len(cells[3].get_text(strip=True)) > 0:
                                collection_date = datetime.strptime(
                                    cells[3].get_text(strip=True), "%A, %d %B %Y"
                                )
                                dict_data = {
                                    "type": bin_type,
                                    "collectionDate": collection_date.strftime(
                                        date_format
                                    ),
                                }
                                data["bins"].append(dict_data)

                            data["bins"].sort(
                                key=lambda x: datetime.strptime(
                                    x.get("collectionDate"), "%d/%m/%Y"
                                )
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
