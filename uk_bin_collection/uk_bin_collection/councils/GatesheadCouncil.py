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
        data = {"bins": []}
        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        web_driver = kwargs.get("web_driver")
        headless= kwargs.get("headless")
        check_paon(user_paon)
        check_postcode(user_postcode)

        # Create Selenium webdriver
        driver = create_webdriver(web_driver,headless)
        driver.get(
            "https://www.gateshead.gov.uk/article/3150/Bin-collection-day-checker"
        )

        # Wait for the postcode field to appear then populate it
        inputElement_postcode = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.ID, "BINCOLLECTIONCHECKER_ADDRESSSEARCH_ADDRESSLOOKUPPOSTCODE")
            )
        )
        inputElement_postcode.send_keys(user_postcode)

        # Click search button
        findAddress = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, "BINCOLLECTIONCHECKER_ADDRESSSEARCH_ADDRESSLOOKUPSEARCH")
            )
        )
        findAddress.click()

        # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//select[@id='BINCOLLECTIONCHECKER_ADDRESSSEARCH_ADDRESSLOOKUPADDRESS']//option[contains(., '"
                    + user_paon
                    + "')]",
                )
            )
        ).click()

        # Wait for the collections table to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".bincollections__table"))
        )

        soup = BeautifulSoup(driver.page_source, features="html.parser")

        # Quit Selenium webdriver to release session
        driver.quit()

        # Get collections table
        table = soup.find("table", {"class": "bincollections__table"})

        # Get rows
        month_year = ""
        for row in table.find_all("tr"):
            if row.find("th"):
                month_year = (
                    row.find("th").get_text(strip=True)
                    + " "
                    + datetime.now().strftime("%Y")
                )
            elif month_year != "":
                collection = row.find_all("td")
                bin_date = datetime.strptime(
                    collection[0].get_text(strip=True) + " " + month_year, "%d %B %Y"
                )
                dict_data = {
                    "type": collection[2]
                    .get_text()
                    .replace("- DAY CHANGE", "")
                    .strip(),
                    "collectionDate": bin_date.strftime(date_format),
                }
                data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return data
