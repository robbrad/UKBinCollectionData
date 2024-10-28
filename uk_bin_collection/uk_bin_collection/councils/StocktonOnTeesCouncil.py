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
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get("https://www.stockton.gov.uk/bin-collection-days")

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (
                        By.ID,
                        "LOOKUPBINDATESBYADDRESSSKIPOUTOFREGION_ADDRESSLOOKUPPOSTCODE",
                    )
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.ID,
                        "LOOKUPBINDATESBYADDRESSSKIPOUTOFREGION_ADDRESSLOOKUPSEARCH",
                    )
                )
            )
            findAddress.click()

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        ""
                        "//*[@id='LOOKUPBINDATESBYADDRESSSKIPOUTOFREGION_ADDRESSLOOKUPADDRESS']//option[contains(., '"
                        + user_paon
                        + "')]",
                    )
                )
            ).click()

            # Wait for the submit button to appear, then click it to get the collection dates
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        '//*[@id="LOOKUPBINDATESBYADDRESSSKIPOUTOFREGION_COLLECTIONDETAILS2"]/div',
                    )
                )
            )
            time.sleep(2)

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            rubbish_div = soup.find(
                "p",
                {
                    "class": "myaccount-block__date myaccount-block__date--bin myaccount-block__date--waste"
                },
            )
            rubbish_date = rubbish_div.text
            if rubbish_date == "Today":
                rubbish_date = datetime.now()
            else:
                rubbish_date = datetime.strptime(
                    remove_ordinal_indicator_from_date_string(rubbish_date).strip(),
                    "%a %d %B %Y",
                ).replace(year=datetime.now().year)

            recycling_div = soup.find(
                "p",
                {
                    "class": "myaccount-block__date myaccount-block__date--bin myaccount-block__date--recycling"
                },
            )
            recycling_date = recycling_div.text
            if recycling_date == "Today":
                recycling_date = datetime.now()
            else:
                recycling_date = datetime.strptime(
                    remove_ordinal_indicator_from_date_string(recycling_date).strip(),
                    "%a %d %B %Y",
                )

            garden_div = soup.find(
                "div",
                {
                    "class": "myaccount-block__item myaccount-block__item--bin myaccount-block__item--garden"
                },
            )
            garden_date = garden_div.find("strong")
            if garden_date.text.strip() == "Date not available":
                print("Garden waste unavailable")
            else:
                if garden_date.text == "Today":
                    garden_date = datetime.now()
                    collections.append(("Garden waste bin", garden_date))
                else:
                    garden_date = datetime.strptime(
                        remove_ordinal_indicator_from_date_string(
                            garden_date.text
                        ).strip(),
                        "%a %d %B %Y",
                    )
                    collections.append(("Garden waste bin", garden_date))

            collections.append(("Rubbish bin", rubbish_date))
            collections.append(("Recycling bin", recycling_date))

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
