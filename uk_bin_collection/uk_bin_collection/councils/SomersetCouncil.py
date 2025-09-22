import datetime

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
            url = kwargs.get("url")
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Use a realistic user agent to help bypass Cloudflare
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get("https://www.somerset.gov.uk/collection-days")

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "postcodeSearch"))
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "govuk-button"))
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
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//h2[contains(@class,'mt-4') and contains(@class,'govuk-heading-s') and normalize-space(.)='Your next collections']",
                    )
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            collections = soup.find_all("div", {"class": "p-2"})

            for collection in collections:
                bin_type = collection.find("h3").get_text()

                next_collection = soup.find("div", {"class": "fw-bold"}).get_text()

                following_collection = soup.find(
                    lambda t: (
                        t.name == "div"
                        and t.get_text(strip=True).lower().startswith("followed by")
                    )
                ).get_text()

                next_collection_date = datetime.strptime(next_collection, "%A %d %B")

                following_collection_date = datetime.strptime(
                    following_collection, "followed by %A %d %B"
                )

                current_date = datetime.now()
                next_collection_date = next_collection_date.replace(
                    year=current_date.year
                )
                following_collection_date = following_collection_date.replace(
                    year=current_date.year
                )

                next_collection_date = get_next_occurrence_from_day_month(
                    next_collection_date
                )

                following_collection_date = get_next_occurrence_from_day_month(
                    following_collection_date
                )

                dict_data = {
                    "type": bin_type,
                    "collectionDate": next_collection_date.strftime(date_format),
                }
                data["bins"].append(dict_data)

                dict_data = {
                    "type": bin_type,
                    "collectionDate": following_collection_date.strftime(date_format),
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
