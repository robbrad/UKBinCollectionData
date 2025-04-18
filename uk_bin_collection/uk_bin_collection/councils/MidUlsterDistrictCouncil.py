import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

# import selenium keys
from selenium.webdriver.common.keys import Keys

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
            user_postcode = kwargs.get("postcode")
            if not user_postcode:
                raise ValueError("No postcode provided.")
            check_postcode(user_postcode)
            user_paon = kwargs.get("paon")
            check_paon(user_paon)

            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            driver = create_webdriver(web_driver, headless, None, __name__)
            page = "https://www.midulstercouncil.org/resident/bins-recycling"

            driver.get(page)

            wait = WebDriverWait(driver, 10)
            try:
                accept_cookies_button = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//button/span[contains(text(), 'I Accept Cookies')]",
                        )
                    )
                )
                accept_cookies_button.click()
            except Exception as e:
                print(
                    "Accept cookies button not found or clickable within the specified time."
                )
                pass

            postcode_input = wait.until(
                EC.presence_of_element_located((By.ID, "postcode-search-input"))
            )
            postcode_input.send_keys(user_postcode)

            # Wait for the element to be clickable
            postcode_search_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Go')]")
                )
            )

            postcode_search_btn.click()

            address_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//button[contains(text(), '{user_paon}')]")
                )
            )
            address_btn.send_keys(Keys.RETURN)

            results_heading = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h3[contains(text(), 'Collection day:')]")
                )
            )

            results = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div/h3[contains(text(), 'My address:')]/parent::div")
                )
            )

            soup = BeautifulSoup(
                results.get_attribute("innerHTML"), features="html.parser"
            )
            data = {"bins": []}

            # 1. Extract the date string
            try:
                date_span = soup.select_one("h2.collection-day span.date-text")
                if date_span:
                    date_text = date_span.text.strip()
                    current_year = datetime.now().year
                    full_date = f"{date_text} {current_year}"  # e.g., "18 Apr 2025"
                    collection_date = datetime.strptime(full_date, "%d %b %Y").strftime(
                        date_format
                    )
                else:
                    collection_date = None
            except Exception as e:
                print(f"Failed to parse date: {e}")
                collection_date = None

            # 2. Extract bin types
            if collection_date:
                bin_blocks = soup.select("div.bin")
                for bin_block in bin_blocks:
                    bin_title_div = bin_block.select_one("div.bin-title")
                    if bin_title_div:
                        bin_type = bin_title_div.get_text(strip=True)
                        data["bins"].append(
                            {
                                "type": bin_type,
                                "collectionDate": collection_date,
                            }
                        )

            # 3. Optional: sort bins by collectionDate
            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
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
