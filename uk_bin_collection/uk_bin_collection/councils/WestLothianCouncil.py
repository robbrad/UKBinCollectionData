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
        headless = kwargs.get("headless")
        check_paon(user_paon)
        check_postcode(user_postcode)

        # Create Selenium webdriver
        driver = create_webdriver(web_driver, headless)
        driver.get(
            "https://www.westlothian.gov.uk/article/31528/Bin-Collection-Calendar-Dates"
        )

        # Close feedback banner
        feedbackBanner = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".feedback__link--no"))
        )
        feedbackBanner.click()

        # Wait for the postcode field to appear then populate it
        inputElement_postcode = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.ID, "WLBINCOLLECTION_PAGE1_ADDRESSLOOKUPPOSTCODE")
            )
        )
        inputElement_postcode.send_keys(user_postcode)

        # Click search button
        findAddress = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.ID, "WLBINCOLLECTION_PAGE1_ADDRESSLOOKUPSEARCH")
            )
        )
        findAddress.click()

        # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//select[@id='WLBINCOLLECTION_PAGE1_ADDRESSLOOKUPADDRESS']//option[contains(., '"
                    + user_paon
                    + "')]",
                )
            )
        ).click()

        # Wait for the collections table to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".bin-collections"))
        )

        soup = BeautifulSoup(driver.page_source, features="html.parser")

        # Quit Selenium webdriver to release session
        driver.quit()

        # Get collections
        for collection in soup.find_all("div", {"class": "bin-collect"}):
            dict_data = {
                "type": collection.find("h3").get_text(strip=True),
                "collectionDate": datetime.strptime(
                    remove_ordinal_indicator_from_date_string(
                        collection.find(
                            "span", {"class": "bin-collect__date"}
                        ).get_text(strip=True)
                    ),
                    "%A, %B %d %Y",
                ).strftime(date_format),
            }
            data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return data
