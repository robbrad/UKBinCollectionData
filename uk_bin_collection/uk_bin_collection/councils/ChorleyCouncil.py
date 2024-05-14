import time
import urllib.parse
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def format_bin_type(bin_colour: str):
    bin_types = {
        "grey": "Garden waste (Grey Bin)",
        "brown": "Paper and card (Brown Bin)",
        "blue": "Bottles and cans (Blue Bin)",
        "green": "General waste (Green Bin)",
    }
    bin_colour = urllib.parse.unquote(bin_colour).split(" ")[0].lower()
    return bin_types[bin_colour]


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
            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_uprn(user_uprn)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent)
            driver.get("https://myaccount.chorley.gov.uk/wastecollections.aspx")

            # Accept cookies banner
            cookieBanner = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "PrivacyPolicyNotification"))
            )
            cookieClose = cookieBanner.find_element(
                By.CSS_SELECTOR, "span.ui-icon-circle-close"
            )
            cookieClose.click()

            # Populate postcode field
            inputElement_postcode = driver.find_element(
                By.ID,
                "MainContent_addressSearch_txtPostCodeLookup",
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.ID,
                        "MainContent_addressSearch_btnFindAddress",
                    )
                )
            )
            findAddress.click()

            time.sleep(1)

            # Wait for the 'Select address' dropdown to appear and select option matching UPRN
            dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.ID,
                        "MainContent_addressSearch_ddlAddress",
                    )
                )
            )
            # Create a 'Select' for it, then select the matching URPN option
            dropdownSelect = Select(dropdown)
            dropdownSelect.select_by_value(user_uprn)

            # Wait for the submit button to appear, then click it to get the collection dates
            submit = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "MainContent_btnSearch"))
            )
            submit.click()

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Get the property details
            property_details = soup.find(
                "table",
                {"class": "WasteCollection"},
            )

            # Get the dates
            for row in property_details.tbody.find_all("tr", recursive=False):
                month_col = row.td
                month = month_col.get_text(strip=True)

                for date_col in month_col.find_next_siblings("td"):
                    day = date_col.p.contents[0].strip()

                    if day == "":
                        continue

                    for bin_type in date_col.find_all("img"):
                        bin_colour = bin_type.get("src").split("/")[-1].split(".")[0]
                        date_object = datetime.strptime(f"{day} {month}", "%d %B %Y")
                        date_formatted = date_object.strftime("%d/%m/%Y")

                        dict_data = {
                            "type": format_bin_type(bin_colour),
                            "collectionDate": date_formatted,
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
