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
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_uprn(user_uprn)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(
                "https://my.eastsuffolk.gov.uk/service/Bin_collection_dates_finder"
            )

            # Wait for iframe to load and switch to it
            WebDriverWait(driver, 30).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "fillform-frame-1"))
            )

            # Wait for postcode entry box
            postcode = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "alt_postcode_search"))
            )
            # Enter postcode
            postcode.send_keys(user_postcode.replace(" ", ""))

            # Wait for address selection dropdown to appear
            address = Select(
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, "alt_choose_address"))
                )
            )

            # Wait for spinner to disappear (signifies options are loaded for select)
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "spinner-outer"))
            )

            # Sometimes the options aren't fully there despite the spinner being gone, wait another 2 seconds.
            sleep(2)

            # Select address by UPRN
            address.select_by_value(user_uprn)

            # Wait for spinner to disappear (signifies data is loaded)
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "spinner-outer"))
            )

            sleep(2)

            # Find data table
            data_table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        '//div[@data-field-name="collection_details"]/div[contains(@class, "fieldContent")]/div[contains(@class, "repeatable-table-wrapper")]',
                    )
                )
            )

            # Make a BS4 object
            soup = BeautifulSoup(
                data_table.get_attribute("innerHTML"), features="html.parser"
            )

            data = {"bins": []}

            rows = soup.find("table").find("tbody").find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                bin_type = cols[2].find_all("span")[1].text.title()
                collection_date = cols[3].find_all("span")[1].text
                collection_date = datetime.strptime(
                    collection_date, "%d/%m/%Y"
                ).strftime(date_format)
                dict_data = {"type": bin_type, "collectionDate": collection_date}
                data["bins"].append(dict_data)

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
