import re
import time

import requests
from bs4 import BeautifulSoup
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
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)
            bindata = {"bins": []}

            URI = "https://hertsmere-services.onmats.com/w/webpage/round-search"

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(URI)

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (
                        By.CLASS_NAME,
                        "relation_path_type_ahead_search",
                    )
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            # Wait for results to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ul.result_list li")
                )
            )
            
            # Use JavaScript to click the correct address
            # Add space after house number to match exactly (e.g., "1 " not "10", "11", etc.)
            driver.execute_script(f"""
                const results = document.querySelectorAll('ul.result_list li');
                for (let li of results) {{
                    const ariaLabel = li.getAttribute('aria-label');
                    if (ariaLabel && ariaLabel.startsWith('{user_paon} ')) {{
                        li.click();
                        return;
                    }}
                }}
            """)

            WebDriverWait(driver, timeout=10).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "input.fragment_presenter_template_edit.btn.bg-primary.btn-medium[type='submit']",
                    )
                )
            ).click()

            WebDriverWait(driver, timeout=10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h3[contains(text(), 'Collection days')]")
                )
            )

            soup = BeautifulSoup(driver.page_source, "html.parser")

            table = soup.find("table", class_="table listing table-striped")

            # Check if the table was found
            if not table:
                raise Exception("Collection schedule table not found.")

            # Extract table rows and cells
            table_data = []
            for row in table.find("tbody").find_all("tr"):
                # Extract cell data from each <td> tag
                row_data = [
                    cell.get_text(strip=True) for cell in row.find_all("td")
                ]
                table_data.append(row_data)

            # The table structure is: [Bin Type, Collection Day, Round Code]
            # All bins are collected on the same day (e.g., "Thursday")
            if not table_data or len(table_data[0]) < 2:
                raise Exception("Unable to parse collection schedule from table.")
            
            collection_day = table_data[0][1]  # e.g., "Thursday"

            # Extract all bin types
            bin_types = []
            for row in table_data:
                if len(row) >= 1 and row[0].strip():
                    bin_types.append(row[0].strip())

            # Calculate next collection dates based on the collection day
            from datetime import datetime, timedelta
            
            days_of_week = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]

            today = datetime.now()
            today_idx = today.weekday()  # Monday is 0 and Sunday is 6
            target_idx = days_of_week.index(collection_day)

            days_until_target = (target_idx - today_idx) % 7
            if days_until_target == 0:
                next_day = today
            else:
                next_day = today + timedelta(days=days_until_target)

            # Generate collection dates for the next 12 weeks (all bins collected weekly)
            all_dates = get_dates_every_x_days(next_day, 7, 12)  # 12 collections, every 7 days

            # Assign all bin types to each collection date
            for date in all_dates:
                for bin_type in bin_types:
                    dict_data = {
                        "type": bin_type,
                        "collectionDate": date,
                    }
                    bindata["bins"].append(dict_data)

            bindata["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
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
        return bindata
