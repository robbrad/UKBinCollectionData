from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def parse_collection_date(date_string) -> datetime:
    now = datetime.now()
    if date_string == "is due today":
        return now

    parsed_date = datetime.strptime(date_string, "%A, %d %B").replace(year=now.year)

    if now.month == 12 and parsed_date.month < 12:
        parsed_date = parsed_date.replace(year=(now.year + 1))

    return parsed_date

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
        council_url = "https://swale.gov.uk/bins-littering-and-the-environment/bins/check-your-bin-day"

        # Create Selenium webdriver
        driver = create_webdriver(web_driver, headless, None, __name__)
        driver.get(council_url)

        # Wait for the postcode field to appear then populate it
        try:
            inputElement_postcode = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "q485476_q1"))
            )
            inputElement_postcode.send_keys(user_postcode)
        except Exception:
            print("Page failed to load. Probably due to Cloudflare robot check!")

        # Click search button
        findAddress = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "form_email_485465_submit"))
        )
        driver.execute_script("arguments[0].click();", findAddress)

        # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//select[@name='q485480:q1']//option[contains(., '"
                    + user_paon
                    + "')]",
                )
            )
        ).click()

        # Click search button
        getBins = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "form_email_485465_submit"))
        )
        driver.execute_script("arguments[0].click();", getBins)

        BinTable = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "SBCYBDSummary"))
        )

        soup = BeautifulSoup(driver.page_source, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        next_collection_date = soup.find(
            "strong", id="SBC-YBD-collectionDate"
        ).text.strip()

        # Extract bins for the next collection
        next_bins = [li.text.strip() for li in soup.select("#SBCFirstBins ul li")]

        # Extract future collection details
        future_collection_date_tag = soup.find(
            "p", text=lambda t: t and "starting from" in t
        )
        future_collection_date = (
            future_collection_date_tag.text.split("starting from")[-1].strip()
            if future_collection_date_tag
            else "No future date found"
        )

        future_bins = [li.text.strip() for li in soup.select("#FirstFutureBins li")]

        for bin in next_bins:
            dict_data = {
                "type": bin,
                "collectionDate": datetime.strptime(
                    next_collection_date, "%A, %d %B"
                ).strftime(date_format),
            }
            data["bins"].append(dict_data)

        for bin in future_bins:
            dict_data = {
                "type": bin,
                "collectionDate": datetime.strptime(
                    future_collection_date, "%A, %d %B"
                ).strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
