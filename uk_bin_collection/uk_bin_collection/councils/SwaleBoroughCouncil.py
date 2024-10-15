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
        # Get postcode and UPRN from kwargs
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        web_driver = kwargs.get("web_driver")
        headless = kwargs.get("headless")
        check_postcode(user_postcode)
        check_paon(user_paon)

        # Build URL to parse
        council_url = "https://swale.gov.uk/bins-littering-and-the-environment/bins/my-collection-day"

        # Create Selenium webdriver
        driver = create_webdriver(web_driver, headless, None, __name__)
        driver.get(council_url)

        # Wait for the postcode field to appear then populate it
        try:
            inputElement_postcode = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "q462406_q1"))
            )
            inputElement_postcode.send_keys(user_postcode)
        except Exception:
            print("Page failed to load. Probably due to Cloudflare robot check!")

        # Click search button
        findAddress = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "form_email_462397_submit"))
        )
        driver.execute_script("arguments[0].click();", findAddress)

        # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//select[@id='SBCYBDAddressList']//option[contains(., '"
                    + user_paon
                    + "')]",
                )
            )
        ).click()

        # Click search button
        getBins = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "form_email_462397_submit"))
        )
        driver.execute_script("arguments[0].click();", getBins)

        BinTable = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "SBC-YBD-Main"))
        )

        soup = BeautifulSoup(driver.page_source, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        # Get the collection bullet points on the page and parse them
        nextCollections = soup.find("div", {"id": "nextCollections"})
        for c in nextCollections:
            collection = c.find_all("strong")
            for bin in collection:
                split = (bin.text).split(" on ")
                bin_type = split[0]
                bin_date = datetime.strptime(split[1], "%A %d %b %Y").strftime(
                    "%d/%m/%Y"
                )
                dict_data = {"type": bin_type, "collectionDate": bin_date}
                data["bins"].append(dict_data)

        return data
