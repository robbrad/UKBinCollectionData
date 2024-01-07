from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# This script pulls (in one hit) the data from Bromley Council Bins Data
import datetime
from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
import time


def get_month_number(month_name):
    return datetime.strptime(month_name, "%B").month


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # UPRN is street id here
        uprn = kwargs.get("uprn")
        check_uprn(uprn)
        web_driver = kwargs.get("web_driver")
        headless = kwargs.get("headless")
        driver = create_webdriver(web_driver, headless)
        driver.get(kwargs.get("url"))

        wait = WebDriverWait(driver, 30)
        roadid = wait.until(
            EC.presence_of_element_located((By.XPATH, '//select[@name="roadID"]'))
        )
        dropdown = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//select[@name="roadID"]'))
        )

        # Create a 'Select' for it, then select the first address in the list
        # (Index 0 is "Make a selection from the list")
        dropdownSelect = Select(dropdown)
        dropdownSelect.select_by_value(str(uprn))
        search_btn = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    '//*[@id="wasteCalendarContainer"]/form/input[@value="Search"]',
                )
            )
        )
        search_btn.click()

        results = wait.until(
            EC.presence_of_element_located((By.ID, "wasteCalendarContainer"))
        )

        # Make a BS4 object
        soup = BeautifulSoup(driver.page_source, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        # Find all calendar containers
        calendar_containers = soup.select(".calendarContainer > .calendarContainer")

        # List to store dictionaries for each item
        data_list = []

        # Iterate through each calendar container
        for container in calendar_containers:
            # Find the header (h2 element) inside the current calendar container
            header = container.find("h2")

            # Extract month and year from the header
            if header:
                month_year = header.get_text(strip=True)
                month, year = month_year.split()

                # Find all elements with class "pink" and "normal" inside the current calendar container
                pink_days = container.find_all("td", class_="pink")
                normal_days = container.find_all("td", class_="normal")
                month_number = get_month_number(month)
                # Extract the dates for "pink" and "normal" days and create dictionary items
                for date in pink_days + normal_days:
                    day = date.get_text().zfill(2)
                    formatted_date = f"{day}/{month_number:02d}/{year}"

                    # Build dictionary for each item
                    dict_data = {
                        "type": "Pink" if date["class"][0] == "pink" else "Normal",
                        "collectionDate": formatted_date,
                    }
                    data["bins"].append(dict_data)
            else:
                print("Invalid calendar format encountered.")

        return data
