import time

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
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
            collections = []
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            # driver = create_webdriver(web_driver, headless)
            driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install())
            )
            driver.get("https://www.westberks.gov.uk/binday")

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.ID, "FINDYOURBINDAYS_ADDRESSLOOKUPPOSTCODE")
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "FINDYOURBINDAYS_ADDRESSLOOKUPSEARCH")
                )
            )
            findAddress.click()

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        ""
                        "//*[@id='FINDYOURBINDAYS_ADDRESSLOOKUPADDRESS']//option[contains(., '"
                        + user_paon
                        + "')]",
                    )
                )
            ).click()

            # Wait for the submit button to appear, then click it to get the collection dates
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="FINDYOURBINDAYS_RUBBISHDATE"]/div')
                )
            )
            time.sleep(2)

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            rubbish_date = datetime.strptime(
                " ".join(
                    soup.find("div", {"id": "FINDYOURBINDAYS_RUBBISHDATE_OUTERDIV"})
                    .get_text(strip=True)
                    .split()[6:8]
                ),
                "%d %B",
            ).replace(year=datetime.now().year)
            recycling_date = datetime.strptime(
                " ".join(
                    soup.find("div", {"id": "FINDYOURBINDAYS_RECYCLINGDATE_OUTERDIV"})
                    .get_text(strip=True)
                    .split()[6:8]
                ),
                "%d %B",
            ).replace(year=datetime.now().year)
            food_date = datetime.strptime(
                " ".join(
                    soup.find("div", {"id": "FINDYOURBINDAYS_FOODWASTEDATE_OUTERDIV"})
                    .get_text(strip=True)
                    .split()[8:10]
                ),
                "%d %B",
            ).replace(year=datetime.now().year)

            if datetime.now().month == 12 and rubbish_date.month == 1:
                rubbish_date = rubbish_date + relativedelta(years=1)
            if datetime.now().month == 12 and recycling_date.month == 1:
                recycling_date = recycling_date + relativedelta(years=1)
            if datetime.now().month == 12 and food_date.month == 1:
                food_date = food_date + relativedelta(years=1)

            collections.append(("Rubbish bin", rubbish_date))
            collections.append(("Recycling bin", recycling_date))
            collections.append(("Food waste bin", food_date))

            ordered_data = sorted(collections, key=lambda x: x[1])
            for item in ordered_data:
                dict_data = {
                    "type": item[0].capitalize(),
                    "collectionDate": item[1].strftime(date_format),
                }
                data["bins"].append(dict_data)

            print()
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
