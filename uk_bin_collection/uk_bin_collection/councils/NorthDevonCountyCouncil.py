from time import sleep
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def wait_for_spinner_or_continue(driver, timeout=10):
    """
    Spinner on North Devon site is unreliable.
    Attempt to wait for it, but continue if it doesn't disappear.
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "spinner-outer"))
        )
    except Exception:
        pass


class CouncilClass(AbstractGetBinDataClass):
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
                "https://my.northdevon.gov.uk/service/WasteRecyclingCollectionCalendar"
            )

            # Switch into iframe
            WebDriverWait(driver, 30).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "fillform-frame-1"))
            )

            # Enter postcode and trigger lookup
            postcode_input = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "postcode_search"))
            )
            postcode_input.clear()
            postcode_input.send_keys(user_postcode.replace(" ", ""))
            postcode_input.send_keys(Keys.RETURN)

            # Wait for address dropdown to populate, fail gracefully if slow
            try:
                WebDriverWait(driver, 25).until(
                    lambda d: len(
                        Select(d.find_element(By.ID, "chooseAddress")).options
                    ) > 1
                )
            except Exception:
                sleep(3)

            # Select address by UPRN
            address_select = Select(driver.find_element(By.ID, "chooseAddress"))

            if not any(opt.get_attribute("value") == user_uprn for opt in address_select.options):
                raise Exception(f"UPRN {user_uprn} not found in address list")

            wait_for_spinner_or_continue(driver, 10)
            sleep(1)

            address_select.select_by_value(user_uprn)

            # Wait for address confirmation
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h2[contains(text(), 'Your address')]")
                )
            )

            wait_for_spinner_or_continue(driver, 10)
            sleep(1)

            # Click Next
            next_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button/span[contains(@class, 'nextText')]")
                )
            )
            next_button.click()

            # Wait for results
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h4[contains(text(), 'Key')]")
                )
            )

            # Find data table
            data_table = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        '//div[@data-field-name="html1"]/div[contains(@class, "fieldContent")]',
                    )
                )
            )

            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(
                data_table.get_attribute("innerHTML"),
                features="html.parser",
            )

            data = {"bins": []}
            waste_sections = soup.find_all("ul", class_="wasteDates")
            current_month_year = None

            for section in waste_sections:
                for li in section.find_all("li", recursive=False):
                    if "MonthLabel" in li.get("class", []):
                        header = li.find("h4")
                        if header:
                            current_month_year = header.text.strip()
                    elif any(
                        bin_class in li.get("class", [])
                        for bin_class in ["BlackBin", "GreenBin", "Recycling"]
                    ):
                        bin_type = li.find("span", class_="wasteType").text.strip()
                        day = li.find("span", class_="wasteDay").text.strip()

                        if current_month_year and day:
                            try:
                                full_date = f"{day} {current_month_year}"
                                collection_date = datetime.strptime(
                                    full_date, "%d %B %Y"
                                ).strftime(date_format)

                                data["bins"].append(
                                    {
                                        "type": bin_type,
                                        "collectionDate": collection_date,
                                    }
                                )
                            except Exception:
                                continue

            # Sort bins by date
            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
            )

            return data

        finally:
            if driver:
                driver.quit()
