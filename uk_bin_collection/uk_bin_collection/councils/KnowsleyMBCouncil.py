import time

from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait


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
            driver = create_webdriver(web_driver, headless)
            driver.get(
                "https://knowsleytransaction.mendixcloud.com/link/youarebeingredirected?target=bincollectioninformation"
            )

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/div[1]/div/div/div/div/div/div[2]/div/div/div/div/div/div[3]/div/div[1]/div/div[1]/div/div/input",
                    )
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            # Wait for address search button, then click it
            addressSearch_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/div[1]/div/div/div/div/div/div[2]/div/div/div/div/div/div[3]/div/div[1]/div/div[2]/div/button",
                    )
                )
            )
            addressSearch_button.click()

            # Wait until the address list has loaded
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/div[1]/div/div/div/div/div/div[2]/div/div/div/div/div/div[3]/div/div[1]/div/div[3]/div/div",
                    )
                )
            )

            # Select the correct address from the list
            addressList_rows = driver.find_elements(By.CLASS_NAME, "row")
            for row in addressList_rows:
                option_name = row.text[0 : len(user_paon)]
                if option_name == user_paon:
                    break
            address_to_select = row.find_element(By.LINK_TEXT, "Choose this address")
            address_to_select.click()

            # Wait for bin dates to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/div[1]/div/div/div/div/div/div[2]/div/div/div/div/div/div[3]/div/div[1]/div/div[4]/div/div",
                    )
                )
            )

            # Parse the HTML from the WebDriver
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            z = soup.find(
                "div", {"class": "mx-name-textBox5 mx-textbox form-group"}
            ).find_next("div", {"class": "form-control-static"})

            maroon_bin_date = datetime.strptime(
                soup.find("div", {"class": "mx-name-textBox3 mx-textbox form-group"})
                .find_next("div", {"class": "form-control-static"})
                .get_text(strip=True),
                "%A %d/%m/%Y",
            )
            collections.append(("Maroon bin", maroon_bin_date))

            grey_bin_date = datetime.strptime(
                soup.find("div", {"class": "mx-name-textBox4 mx-textbox form-group"})
                .find_next("div", {"class": "form-control-static"})
                .get_text(strip=True),
                "%A %d/%m/%Y",
            )
            collections.append(("Grey bin", grey_bin_date))

            blue_bin_date = datetime.strptime(
                soup.find("div", {"class": "mx-name-textBox5 mx-textbox form-group"})
                .find_next("div", {"class": "form-control-static"})
                .get_text(strip=True),
                "%A %d/%m/%Y",
            )
            collections.append(("Blue bin", blue_bin_date))

            ordered_data = sorted(collections, key=lambda x: x[1])
            for item in ordered_data:
                dict_data = {
                    "type": item[0].capitalize(),
                    "collectionDate": item[1].strftime(date_format),
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
