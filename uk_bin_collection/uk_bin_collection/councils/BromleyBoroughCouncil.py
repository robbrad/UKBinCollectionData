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

from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup
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
        # Make a BS4 object

        bin_data_dict = {"bins": []}
        collections = []
        web_driver = kwargs.get("web_driver")

        data = {"bins": []}

        # Get our initial session running
        driver = create_webdriver(web_driver)
        driver.get(kwargs.get("url"))

        wait = WebDriverWait(driver, 30)
        results = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "waste-service-image"))
        )
        # Search for the specific bins in the table using BS
        # Parse the HTML content
        # Find all elements with the class 'container-name' to extract bin types
        # Parse the HTML content
        soup = BeautifulSoup(driver.page_source, "html.parser")
        soup.prettify

        # Find all elements with class 'govuk-summary-list'
        bin_info = []
        waste_services = soup.find_all(
            "h3", class_="govuk-heading-m waste-service-name"
        )

        for service in waste_services:
            service_title = service.get_text(strip=True)
            next_collection = service.find_next_sibling().find(
                "dt", text="Next collection"
            )

            if next_collection:
                next_collection_date = next_collection.find_next_sibling().get_text(
                    strip=True
                )
                # Extract date part and remove the suffix
                next_collection_date_parse = next_collection_date.split(",")[1].strip()
                day = next_collection_date_parse.split()[0]
                month = next_collection_date_parse.split()[1]

                # Remove the suffix (e.g., 'th', 'nd', 'rd', 'st') from the day
                if day.endswith(("th", "nd", "rd", "st")):
                    day = day[:-2]  # Remove the last two characters

                # Reconstruct the date string without the suffix
                date_without_suffix = f"{day} {month}"

                # Parse the date string to a datetime object
                date_object = datetime.strptime(date_without_suffix, "%d %B")

                # Get the current year
                current_year = datetime.now().year

                # Check if the parsed date is in the past compared to the current date
                if date_object < datetime.now():
                    # If the parsed date is in the past, assume it's for the next year
                    current_year += 1
                # Append the year to the date
                date_with_year = date_object.replace(year=current_year)

                # Format the date with the year
                date_with_year_formatted = date_with_year.strftime(
                    "%d/%m/%Y"
                )  # Format the date as '%d/%m/%Y'

                # Create the dictionary with the formatted data
                dict_data = {
                    "type": service_title,
                    "collectionDate": date_with_year_formatted,
                }
                data["bins"].append(dict_data)
        return data
