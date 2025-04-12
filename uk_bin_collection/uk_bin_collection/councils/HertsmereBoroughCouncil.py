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

            URI_1 = "https://www.hertsmere.gov.uk/Environment-Refuse-and-Recycling/Recycling--Waste/Bin-collections/Collections-and-calendar.aspx"
            URI_2 = "https://hertsmere-services.onmats.com/w/webpage/round-search"

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(URI_1)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            current_week = (soup.find("li", class_="current")).text.strip()

            strong = soup.find_all("strong", text=re.compile(r"^Week"))

            bin_weeks = []
            for tag in strong:
                parent = tag.parent
                bin_type = (
                    (parent.text).split("-")[1].strip().replace("\xa0", " ").split(" and ")
                )
                for bin in bin_type:
                    dict_data = {
                        "week": tag.text.replace("\xa0", " "),
                        "bin_type": bin,
                    }
                    bin_weeks.append(dict_data)

            driver.get(URI_2)

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

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f"//ul[@class='result_list']/li[starts-with(@aria-label, '{user_paon}')]",
                    )
                )
            ).click()

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
            if table:
                # Extract table rows and cells
                table_data = []
                for row in table.find("tbody").find_all("tr"):
                    # Extract cell data from each <td> tag
                    row_data = [cell.get_text(strip=True) for cell in row.find_all("td")]
                    table_data.append(row_data)

            else:
                print("Table not found.")

            collection_day = (table_data[0])[1]

            current_week_bins = [bin for bin in bin_weeks if bin["week"] == current_week]
            next_week_bins = [bin for bin in bin_weeks if bin["week"] != current_week]

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

            current_week_dates = get_dates_every_x_days(next_day, 14, 7)
            next_week_date = next_day + timedelta(days=7)
            next_week_dates = get_dates_every_x_days(next_week_date, 14, 7)

            for date in current_week_dates:
                for bin in current_week_bins:
                    dict_data = {
                        "type": bin["bin_type"],
                        "collectionDate": date,
                    }
                    bindata["bins"].append(dict_data)

            for date in next_week_dates:
                for bin in next_week_bins:
                    dict_data = {
                        "type": bin["bin_type"],
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