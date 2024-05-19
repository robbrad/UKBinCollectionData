from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def get_data(self, page) -> dict:
        # Make a BS4 object
        soup = BeautifulSoup(page, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        for month in soup.select('div[class*="bin-collection__month"]'):
            monthName = month.select('h3[class*="bin-collection__title"]')[
                0
            ].text.strip()
            for collectionDay in month.select('li[class*="bin-collection__item"]'):
                bin_type = collectionDay.select('span[class*="bin-collection__type"]')[
                    0
                ].text.strip()
                binCollection = (
                    collectionDay.select('span[class*="bin-collection__day"]')[
                        0
                    ].text.strip()
                    + ", "
                    + collectionDay.select('span[class*="bin-collection__number"]')[
                        0
                    ].text.strip()
                    + " "
                    + monthName
                )

                dict_data = {
                    "type": bin_type,
                    "collectionDate": datetime.strptime(
                        binCollection, "%A, %d %B %Y"
                    ).strftime(date_format),
                }

                data["bins"].append(dict_data)

        return data

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            page = "https://www.highpeak.gov.uk/findyourbinday"

            # Assign user info
            user_postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            # Hide Cookies
            inputElement_hc = driver.find_element(
                By.CLASS_NAME, "cookiemessage__link--close"
            )
            inputElement_hc.click()

            # Enter postcode in text box and wait
            inputElement_pc = driver.find_element(
                By.ID, "FINDBINDAYSHIGHPEAK_POSTCODESELECT_POSTCODE"
            )
            inputElement_pc.send_keys(user_postcode)
            inputElement_pc.send_keys(Keys.ENTER)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "FINDBINDAYSHIGHPEAK_ADDRESSSELECT_ADDRESS")
                )
            )

            # Select address from dropdown and wait
            inputElement_ad = Select(
                driver.find_element(By.ID, "FINDBINDAYSHIGHPEAK_ADDRESSSELECT_ADDRESS")
            )

            inputElement_ad.select_by_visible_text(user_paon)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.ID,
                        "FINDBINDAYSHIGHPEAK_ADDRESSSELECT_ADDRESSSELECTNEXTBTN_NEXT",
                    )
                )
            )

            # Submit address information and wait
            driver.find_element(
                By.ID, "FINDBINDAYSHIGHPEAK_ADDRESSSELECT_ADDRESSSELECTNEXTBTN_NEXT"
            ).click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "FINDBINDAYSHIGHPEAK_CALENDAR_MAINCALENDAR")
                )
            )

            # Read next collection information into Pandas
            table = driver.find_element(
                By.ID, "FINDBINDAYSHIGHPEAK_CALENDAR_MAINCALENDAR"
            ).get_attribute("outerHTML")

            # Parse data into dict
            data = self.get_data(table)
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
