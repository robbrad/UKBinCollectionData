from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
import re  # Import regular expressions

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
            data = {"bins": []}

            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_uprn(user_uprn)
            check_postcode(user_postcode)
            # Create Selenium webdriver
            page = f"https://my.nwleics.gov.uk/my-property-finder?address={user_postcode}&go=1"

            driver = create_webdriver(web_driver, headless)
            driver.get(page)

            # If you bang in the house number (or property name) and postcode in the box it should find your property

            # iframe_presense = WebDriverWait(driver, 30).until(
            #    EC.presence_of_element_located((By.ID, "fillform-frame-1"))
            # )

            # driver.switch_to.frame(iframe_presense)
            wait = WebDriverWait(driver, 60)

            address_link = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, f'//a[contains(@href, "{user_uprn}")]')
                )
            )

            address_link.click()

            refuse_element = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f'//h3[contains(text(), "Refuse Collection Dates")]')
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Find the unordered list containing refuse collection details
            refuse_list = soup.find("ul", class_="refuse")

            current_year = datetime.now().year

            if refuse_list:
                # Iterate through list items within the unordered list
                for li in refuse_list.find_all("li"):
                    date = li.find(
                        "strong", class_="date"
                    ).text.strip()  # Extract the date
                    waste_type = li.find("a").text.strip()  # Extract the waste type

                    # Parse the date from the string
                    # check for today and tomorrow
                    if date.lower() == "today":
                        parsed_date = datetime.now().date()
                    elif date.lower() == "tomorrow":
                        parsed_date = (datetime.now() + timedelta(days=1)).date()
                    else:
                        date = re.sub(r"(st|nd|rd|th)", "", date)
                        parsed_date = datetime.strptime(date, "%a %d %b").date()

                    current_date = datetime.now().date()

                    # double check we've got a year and if not the current one
                    if parsed_date.year < current_date.year:
                        parsed_date = parsed_date.replace(year=current_date.year)

                    # check if the date is in the past and if so add a year
                    if parsed_date < current_date:
                        parsed_date = parsed_date.replace(year=current_date.year + 1)

                    # Append data to your 'bins' list (this replicates your existing logic)
                    data["bins"].append(
                        {
                            "type": waste_type,
                            "collectionDate": parsed_date.strftime("%d/%m/%Y"),
                        }
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
