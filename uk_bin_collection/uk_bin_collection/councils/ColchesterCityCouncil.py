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
            driver.get(
                "https://www.colchester.gov.uk/your-recycling-calendar/?start=true"
            )

            accept_button = WebDriverWait(driver, timeout=30).until(
                EC.element_to_be_clickable((By.ID, "ccc-notify-accept"))
            )
            accept_button.click()

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "input-text"))
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "button-small"))
            )
            findAddress.click()

            # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//select[@class='input-select']//option[contains(., '"
                        + user_paon
                        + "')]",
                    )
                )
            ).click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "button-small"))
            ).click()

            # Wait for the collections table to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "recycling-calendar"))
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            recyclingcalendar = soup.find("div", {"class": "recycling-calendar"})

            rows = recyclingcalendar.find_all(
                "div", {"class": "recycling-calendar-row"}
            )

            for row in rows:
                collectiondate = datetime.strptime(
                    row.find("strong").get_text(),
                    "%d %B %Y",
                )
                listobj = row.find("ul")
                for li in listobj.find_all("li"):
                    dict_data = {
                        "type": li.get_text().strip(),
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
