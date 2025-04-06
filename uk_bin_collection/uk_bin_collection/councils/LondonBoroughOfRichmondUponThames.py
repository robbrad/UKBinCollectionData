from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str, **kwargs) -> dict:
        print(f"Arguments are f{kwargs}")
        driver = None
        try:
            page = kwargs["url"]
            street_name = kwargs.get("paon")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            wait = WebDriverWait(driver, 60)

            self.dismiss_cookie_banner(wait)
            self.input_street_name(street_name, wait)
            self.submit(wait)
            bin_types, collection_days = self.get_bins(driver)
            bindata = self.get_collection_days(bin_types, collection_days)

            print(bindata)

        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return bindata

    def get_collection_days(self, bin_types, collection_days):
        bindata = {"bins": []}
        WEEKLY_COLLECTION = 0
        GARDEN_COLLECTION = 1

        for index, bin_type in enumerate(bin_types):
            # currently only handled weekly and garden collection, special collections like Christmas Day need to be added
            if index == WEEKLY_COLLECTION:
                next_collection_date = get_next_day_of_week(
                    collection_days[index].text.strip(), date_format
                )
            elif index == GARDEN_COLLECTION:
                split_date_part = collection_days[index].text.split("More dates")[0]
                next_collection_date = datetime.strptime(
                    split_date_part.strip(), "%d %B %Y"
                ).strftime(date_format)
            else:
                next_collection_date = datetime.strptime(
                    collection_days[index].text.strip(), "%d %B %Y"
                ).strftime(date_format)

            dict_data = {
                "type": bin_type.text.strip(),
                "collectionDate": next_collection_date,
            }
            bindata["bins"].append(dict_data)
        return bindata

    def get_bins(self, driver):
        table = driver.find_element(By.XPATH, ".//div[@id='maincontent']//table")
        table_rows = table.find_elements(by=By.TAG_NAME, value="tr")
        headerRow = table_rows[0]
        table_info_row = table_rows[1]
        bin_types = headerRow.find_elements(by=By.TAG_NAME, value="th")[2:]
        collection_days = table_info_row.find_elements(by=By.TAG_NAME, value="td")[2:]
        return bin_types, collection_days

    def submit(self, wait):
        main_content_submit_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, ".//div[@id='maincontent']//input[@type='submit']")
            )
        )
        main_content_submit_button.send_keys(Keys.ENTER)

    def input_street_name(self, street_name, wait):
        input_element_postcodesearch = wait.until(
            EC.visibility_of_element_located((By.ID, "Street"))
        )
        input_element_postcodesearch.send_keys(street_name)

    def dismiss_cookie_banner(self, wait):
        cookie_banner = wait.until(
            EC.visibility_of_element_located((By.ID, "ccc-dismiss-button"))
        )
        cookie_banner.send_keys(Keys.ENTER)
