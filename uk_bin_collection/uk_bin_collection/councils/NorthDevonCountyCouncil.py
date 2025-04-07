from time import sleep

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default
    implementation.
    """

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

            # Wait for iframe to load and switch to it
            WebDriverWait(driver, 30).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "fillform-frame-1"))
            )

            # Wait for postcode entry box
            postcode = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "postcode_search"))
            )
            # Enter postcode
            postcode.send_keys(user_postcode.replace(" ", ""))

            # Wait for address selection dropdown to appear
            address = Select(
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, "chooseAddress"))
                )
            )

            # Wait for spinner to disappear (signifies options are loaded for select)
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located(
                    (By.CLASS_NAME, "spinner-outer")
                )  # row-fluid spinner-outer
            )

            # Sometimes the options aren't fully there despite the spinner being gone, wait another 2 seconds.
            sleep(2)

            # Select address by UPRN
            address.select_by_value(user_uprn)

            # Wait for spinner to disappear (signifies data is loaded)
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "spinner-outer"))
            )

            sleep(2)

            address_confirmation = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h2[contains(text(), 'Your address')]")
                )
            )

            next_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button/span[contains(@class, 'nextText')]")
                )
            )

            next_button.click()

            results = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h4[contains(text(), 'Key')]")
                )
            )

            # Find data table
            data_table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        '//div[@data-field-name="html1"]/div[contains(@class, "fieldContent")]',
                    )
                )
            )

            # Make a BS4 object
            soup = BeautifulSoup(
                data_table.get_attribute("innerHTML"), features="html.parser"
            )

            # Initialize the data dictionary
            data = {"bins": []}

            # Loop through each list of waste dates
            waste_sections = soup.find_all("ul", class_="wasteDates")

            current_month_year = None

            for section in waste_sections:
                for li in section.find_all("li", recursive=False):
                    if "MonthLabel" in li.get("class", []):
                        # Extract month and year (e.g., "April 2025")
                        header = li.find("h4")
                        if header:
                            current_month_year = header.text.strip()
                    elif any(
                        bin_class in li.get("class", [])
                        for bin_class in ["BlackBin", "GreenBin", "Recycling"]
                    ):
                        bin_type = li.find("span", class_="wasteType").text.strip()
                        day = li.find("span", class_="wasteDay").text.strip()
                        weekday = li.find("span", class_="wasteName").text.strip()

                        if current_month_year and day:
                            try:
                                full_date = f"{day} {current_month_year}"
                                collection_date = datetime.strptime(
                                    full_date, "%d %B %Y"
                                ).strftime(date_format)
                                dict_data = {
                                    "type": bin_type,
                                    "collectionDate": collection_date,
                                }
                                data["bins"].append(dict_data)
                            except Exception as e:
                                print(f"Skipping invalid date '{full_date}': {e}")

            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
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
