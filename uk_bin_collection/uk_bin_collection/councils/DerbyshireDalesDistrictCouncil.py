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
        page = "https://selfserve.derbyshiredales.gov.uk/renderform.aspx?t=103&k=9644C066D2168A4C21BCDA351DA2642526359DFF"

        data = {"bins": []}

        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        web_driver = kwargs.get("web_driver")
        headless= kwargs.get("headless")
        check_uprn(user_uprn)
        check_postcode(user_postcode)

        # Create Selenium webdriver
        driver = create_webdriver(web_driver,headless)
        driver.get(page)

        # Populate postcode field
        inputElement_postcode = driver.find_element(
            By.ID,
            "ctl00_ContentPlaceHolder1_FF2924TB",
        )
        inputElement_postcode.send_keys(user_postcode)

        # Click search button
        driver.find_element(
            By.ID,
            "ctl00_ContentPlaceHolder1_FF2924BTN",
        ).click()

        # Wait for the 'Select address' dropdown to appear and select option matching UPRN
        dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, "ctl00_ContentPlaceHolder1_FF2924DDL")
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

        # Quit Selenium webdriver to release session
        driver.quit()

        bin_rows = (
            soup.find("div", id="ctl00_ContentPlaceHolder1_pnlConfirmation")
            .find("div", {"class": "row"})
            .find_all("div", {"class": "row"})
        )
        if bin_rows:
            for bin_row in bin_rows:
                bin_data = bin_row.find_all("div")
                if bin_data and bin_data[0] and bin_data[1]:
                    collection_date = datetime.strptime(
                        bin_data[0].get_text(strip=True), "%A%d %B, %Y"
                    )
                    dict_data = {
                        "type": bin_data[1].get_text(strip=True),
                        "collectionDate": collection_date.strftime(date_format),
                    }
                    data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
