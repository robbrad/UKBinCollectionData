import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

date_format = "%d/%m/%Y"

class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            page = "https://www.chichester.gov.uk/checkyourbinday"

            user_postcode = kwargs.get("postcode")
            house_number = kwargs.get("paon")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            wait = WebDriverWait(driver, 60)

            input_postcode = wait.until(
                EC.visibility_of_element_located(
                    (By.ID, "WASTECOLLECTIONCALENDARV5_CALENDAR_ADDRESSLOOKUPPOSTCODE")
                )
            )
            input_postcode.send_keys(user_postcode)

            search_button = wait.until(
                EC.element_to_be_clickable(
                    (By.ID, "WASTECOLLECTIONCALENDARV5_CALENDAR_ADDRESSLOOKUPSEARCH")
                )
            )
            search_button.send_keys(Keys.ENTER)

            self.smart_select_address(driver, house_number)

            wait.until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "bin-collection-dates-container")
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            table = soup.find("table", class_="defaultgeneral bin-collection-dates")
            rows = table.find_all("tr") if table else []

            bin_collection_data = []
            for row in rows:
                cells = row.find_all("td")
                if cells:
                    date_str = cells[0].text.strip()
                    bin_type = cells[1].text.strip()
                    date_obj = datetime.strptime(date_str, "%d %B %Y")
                    formatted_date = date_obj.strftime(date_format)
                    bin_collection_data.append({
                        "collectionDate": formatted_date,
                        "type": bin_type
                    })

            print(bin_collection_data)

            return {"bins": bin_collection_data}

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()

    def smart_select_address(self, driver, house_number: str):
        dropdown_id = "WASTECOLLECTIONCALENDARV5_CALENDAR_ADDRESSLOOKUPADDRESS"

        print("Waiting for address dropdown...")

        def dropdown_has_addresses(d):
            try:
                dropdown_el = d.find_element(By.ID, dropdown_id)
                select = Select(dropdown_el)
                return len(select.options) > 1
            except StaleElementReferenceException:
                return False

        WebDriverWait(driver, 30).until(dropdown_has_addresses)

        dropdown_el = driver.find_element(By.ID, dropdown_id)
        dropdown = Select(dropdown_el)

        print("Address dropdown options:")
        for opt in dropdown.options:
            print(f"- {opt.text.strip()}")

        user_input_clean = house_number.lower().strip()
        found = False

        for option in dropdown.options:
            option_text_clean = option.text.lower().strip()
            print(f"Comparing: {repr(option_text_clean)} == {repr(user_input_clean)}")

            if (
                option_text_clean == user_input_clean
                or option_text_clean.startswith(f"{user_input_clean},")
            ):
                try:
                    option.click()
                    found = True
                    print(f"Strict match clicked: {option.text.strip()}")
                    break
                except StaleElementReferenceException:
                    print("Stale during click, retrying...")
                    dropdown_el = driver.find_element(By.ID, dropdown_id)
                    dropdown = Select(dropdown_el)
                    for fresh_option in dropdown.options:
                        if fresh_option.text.lower().strip() == option_text_clean:
                            fresh_option.click()
                            found = True
                            print(f"Strict match clicked after refresh: {fresh_option.text.strip()}")
                            break

            if found:
                break

        if not found:
            print("No strict match found, trying fuzzy match...")
            for option in dropdown.options:
                option_text_clean = option.text.lower().strip()
                if user_input_clean in option_text_clean:
                    try:
                        option.click()
                        found = True
                        print(f"Fuzzy match clicked: {option.text.strip()}")
                        break
                    except StaleElementReferenceException:
                        print("Stale during fuzzy click, retrying...")
                        dropdown_el = driver.find_element(By.ID, dropdown_id)
                        dropdown = Select(dropdown_el)
                        for fresh_option in dropdown.options:
                            if fresh_option.text.lower().strip() == option_text_clean:
                                fresh_option.click()
                                found = True
                                print(f"Fuzzy match clicked after refresh: {fresh_option.text.strip()}")
                                break

                if found:
                    break

        if not found:
            all_opts = [opt.text.strip() for opt in dropdown.options]
            raise Exception(
                f"Could not find address '{house_number}' in options: {all_opts}"
            )