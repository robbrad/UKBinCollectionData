import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

import re


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        try:
            data = {"bins": []}

            user_paon = kwargs.get("paon")
            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            driver = create_webdriver(web_driver, headless, None, __name__)

            page = "https://www.middlesbrough.gov.uk/recycling-and-rubbish/bin-collection-dates/"
            driver.get(page)

            address_box = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located((By.ID, "row-input-0"))
            )
            address_box.click()
            address_box.send_keys(user_paon)

            search_button = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located((By.ID, "rCbtn-search"))
            )
            search_button.click()

            iframe_presense = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "recollect-frame"))
            )
            driver.switch_to.frame(iframe_presense)

            results = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located((By.ID, "rCpage-place_calendar"))
            )

            html_content = driver.page_source
            soup = BeautifulSoup(html_content, "html.parser")

            calendar_section = soup.find("section", {"id": "alt-calendar-list"})
            if not calendar_section:
                raise ValueError("Calendar section not found in the HTML.")

            date_headers = calendar_section.find_all("h3")
            collection_lists = calendar_section.find_all("ul")

            current_month = datetime.now().month
            current_year = datetime.now().year

            for date_header, collection_list in zip(date_headers, collection_lists):
                raw_date = date_header.text.strip()

                # **Regex to match "Wednesday, February 19" format**
                match = re.match(r"([A-Za-z]+), ([A-Za-z]+) (\d{1,2})", raw_date)

                if match:
                    day_name, month_name, day_number = (
                        match.groups()
                    )  # Extract components
                    extracted_month = datetime.strptime(month_name, "%B").month
                    extracted_day = int(day_number)

                    # Handle Dec-Jan rollover: If month is before the current month, assume next year
                    inferred_year = (
                        current_year + 1
                        if extracted_month < current_month
                        else current_year
                    )

                    # **Correct the raw_date format before parsing**
                    raw_date = f"{day_name}, {month_name} {day_number}, {inferred_year}"

                print(
                    f"DEBUG: Final raw_date before parsing -> {raw_date}"
                )  # Debugging output

                # Convert to required format (%d/%m/%Y)
                try:
                    parsed_date = datetime.strptime(raw_date, "%A, %B %d, %Y")
                    formatted_date = parsed_date.strftime(date_format)
                except ValueError:
                    raise ValueError(f"Date format error after inference: {raw_date}")

                for li in collection_list.find_all("li"):
                    bin_type = li.get_text(strip=True).split(".")[0]
                    data["bins"].append(
                        {"type": bin_type, "collectionDate": formatted_date}
                    )

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()

        return data
