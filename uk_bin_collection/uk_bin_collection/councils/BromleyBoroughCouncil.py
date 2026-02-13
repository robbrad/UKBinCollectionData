# This script pulls (in one hit) the data from Bromley Council Bins Data
import datetime
from datetime import datetime

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

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
            bin_data_dict = {"bins": []}
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            data = {"bins": []}

            # Get our initial session running
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get(kwargs.get("url"))

            wait = WebDriverWait(driver, 30)
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "waste-service-image"))
            )

            # Parse the HTML content
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Find all elements with class 'govuk-summary-list'
            waste_services = soup.find_all("div", class_="waste-service-grid")

            for service in waste_services:
                waste_service_name = service.find(
                    "h3", class_="govuk-heading-m waste-service-name"
                )
                service_title = waste_service_name.get_text(strip=True)
                list_row = service.find_all("div", class_="govuk-summary-list__row")
                for row in list_row:
                    next_collection = row.find("dt", string="Next collection")

                    if next_collection:
                        next_collection_date = (
                            next_collection.find_next_sibling().get_text(strip=True)
                        )
                        # Extract date part and remove the suffix
                        next_collection_date_parse = next_collection_date.split(",")[
                            1
                        ].strip()
                        day, month = next_collection_date_parse.split()[:2]

                        day = remove_ordinal_indicator_from_date_string(day)

                        # Reconstruct the date string without the suffix
                        date_without_suffix = f"{day} {month}"

                        # Parse the date string to a datetime object
                        date_object = datetime.strptime(date_without_suffix, "%d %B")

                        # Get the current year
                        current_year = datetime.now().year

                        # Append the year to the date
                        date_with_year = date_object.replace(year=current_year)

                        # Check if the parsed date is in the past compared to the current date
                        if date_object < datetime.now():
                            # If the parsed date is in the past, assume it's for the next year
                            current_year += 1

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
