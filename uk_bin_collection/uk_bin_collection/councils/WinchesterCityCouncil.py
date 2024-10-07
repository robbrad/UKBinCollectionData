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
            driver.get("http://www.winchester.gov.uk/bin-calendar")

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "postcodeSearch"))
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//button[@class="govuk-button mt-4"]')
                )
            )
            findAddress.click()

            # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//select[@id='addressSelect']//option[contains(., '"
                        + user_paon
                        + "')]",
                    )
                )
            ).click()

            # Wait for the collections table to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        '//div[@class="ant-row d-flex justify-content-between mb-4 mt-2 css-2rgkd4"]',
                    )
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            recyclingcalendar = soup.find(
                "div",
                {
                    "class": "ant-row d-flex justify-content-between mb-4 mt-2 css-2rgkd4"
                },
            )

            rows = recyclingcalendar.find_all(
                "div",
                {
                    "class": "ant-col ant-col-xs-12 ant-col-sm-12 ant-col-md-12 ant-col-lg-12 ant-col-xl-12 css-2rgkd4"
                },
            )

            current_year = datetime.now().year
            current_month = datetime.now().month

            for row in rows:
                BinType = row.find("h3").text
                collectiondate = datetime.strptime(
                    row.find("div", {"class": "text-white fw-bold"}).text,
                    "%A %d %B",
                )
                if (current_month > 10) and (collectiondate.month < 3):
                    collectiondate = collectiondate.replace(year=(current_year + 1))
                else:
                    collectiondate = collectiondate.replace(year=current_year)

                dict_data = {
                    "type": BinType,
                    "collectionDate": collectiondate.strftime("%d/%m/%Y"),
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
