from time import sleep

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

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
            page = "https://www.horsham.gov.uk/waste-recycling-and-bins/household-bin-collections/check-your-bin-collection-day"

            bin_data = {"bins": []}

            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_uprn(user_uprn)
            check_postcode(user_postcode)
            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            # Accept cookies
            try:
                accept_cookies = WebDriverWait(driver, timeout=10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[@id='ccc-notify-accept']")
                    )
                )
                accept_cookies.click()
            except:
                print(
                    "Accept cookies banner not found or clickable within the specified time."
                )
                pass
            # Wait for postcode entry box

            postcode_input = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@value='Enter your postcode']")
                )
            )

            postcode_input.send_keys(user_postcode)
            search_btn = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located((By.ID, "Submit1"))
            )
            search_btn.click()

            address_results = Select(
                WebDriverWait(driver, timeout=15).until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "//option[contains(text(),'Please select address...')]/parent::select",
                        )
                    )
                )
            )

            address_results.select_by_value(user_uprn)

            results = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//th[contains(text(),'COLLECTION TYPE')]/ancestor::table",
                    )
                )
            )

            soup = BeautifulSoup(
                results.get_attribute("innerHTML"), features="html.parser"
            )

            # Skip the header, loop through each row in tbody
            for row in soup.find_all("tbody")[0].find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue
                date_str = cells[1].get_text(strip=True)
                collection_type = cells[2].get_text(strip=True)

                try:
                    date = datetime.strptime(date_str, "%d/%m/%Y").strftime(date_format)
                except ValueError:
                    continue  # Skip if date is invalid

                bin_data["bins"].append(
                    {"type": collection_type, "collectionDate": date}
                )

            # Sort by date
            bin_data["bins"].sort(
                key=lambda x: datetime.strptime(x["collectionDate"], date_format)
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
        return bin_data
