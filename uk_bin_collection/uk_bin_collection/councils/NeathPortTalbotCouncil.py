import time

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
            data = {"bins": []}
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get("https://beta.npt.gov.uk/bins-and-recycling/bin-day-finder/")

            # Accept cookies banner
            cookieAccept = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "ccc-notify-accept"))
            )
            cookieAccept.click()

            # Populate postcode field
            inputElement_postcode = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.ID,
                        "PostCode",
                    )
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//button[@value='Find address']",
                    )
                )
            )
            findAddress.click()

            # Wait for the 'Select address' dropdown to appear and select option matching UPRN
            dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.ID,
                        "Address",
                    )
                )
            )
            # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//select[@ID='Address']//option[contains(., '"
                        + user_paon
                        + "')]",
                    )
                )
            ).click()

            # Wait for the submit button to appear, then click it to get the collection dates
            submit = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//input[@value='Find bin day']",
                    )
                )
            )
            submit.click()

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            soup = soup.find(
                "div",
                {"id": "contentInner"},
            )

            soup = soup.find("div", class_="umb-block-grid__layout-item")

            # Get the dates
            for date in soup.find_all("h2"):
                date_text = date.get_text(strip=True)
                if date_text != "Bank Holidays":
                    try:
                        bin_date = datetime.strptime(
                            date_text
                            .removesuffix("(Today)")
                            .removesuffix("(Tomorrow)")
                            .replace("&nbsp", " ")
                            + " "
                            + datetime.now().strftime("%Y"),
                            "%A, %d %B %Y",
                        )
                        bin_types_wrapper = date.find_next_sibling("div")
                        for bin_type_wrapper in bin_types_wrapper.find_all(
                            "div",
                            {
                                "class": "card-body ps-5 ps-md-4 ps-lg-5 position-relative bg-white"
                            },
                        ):
                            if bin_date and bin_type_wrapper:
                                bin_type = bin_type_wrapper.find("a").get_text(strip=True)
                                bin_type += (
                                    " ("
                                    + bin_type_wrapper.find("span").get_text(strip=True)
                                    + ")"
                                )
                                dict_data = {
                                    "type": bin_type,
                                    "collectionDate": bin_date.strftime(date_format),
                                }
                                data["bins"].append(dict_data)
                    except ValueError:
                        # Skip h2 elements that aren't dates (e.g., popup notices)
                        continue

            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
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
