import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
            user_uprn = kwargs.get("uprn")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            page = f"https://waste.bexley.gov.uk/waste/{user_uprn}"

            print(f"Trying URL: {page}")  # Debug

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            # Wait for the main content container to be present
            wait = WebDriverWait(driver, 30)  # Increased timeout to 30 seconds

            # First wait for container
            main_content = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "/html/body/div[1]/div/div[2]/div")
                )
            )

            # Then wait for loading indicator to disappear
            wait.until(EC.invisibility_of_element_located((By.ID, "loading-indicator")))

            # Add after the loading indicator wait
            time.sleep(3)  # Give extra time for JavaScript to populate the data

            # Then wait for at least one bin section to appear
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "waste-service-name"))
            )

            # Now parse the page content
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            data = {"bins": []}
            bin_sections = soup.find_all("h3", class_="waste-service-name")

            if not bin_sections:
                print("No bin sections found after waiting for content")
                print(f"Page source: {driver.page_source}")
                return data

            # Rest of your existing bin processing code
            for bin_section in bin_sections:
                # Extract the bin type (e.g., "Brown Caddy", "Green Wheelie Bin", etc.)
                bin_type = bin_section.get_text(strip=True).split("\n")[
                    0
                ]  # The first part is the bin type

                # Find the next sibling <dl> tag that contains the next collection information
                summary_list = bin_section.find_next("dl", class_="govuk-summary-list")

                if summary_list:
                    # Now, instead of finding by class, we'll search by text within the dt element
                    next_collection_dt = summary_list.find(
                        "dt", string=lambda text: "Next collection" in text
                    )

                    if next_collection_dt:
                        # Find the sibling <dd> tag for the collection date
                        next_collection = next_collection_dt.find_next_sibling(
                            "dd"
                        ).get_text(strip=True)

                        if next_collection:
                            try:
                                # Parse the next collection date (assuming the format is like "Tuesday 15 October 2024")
                                parsed_date = datetime.strptime(
                                    next_collection, "%A %d %B %Y"
                                )

                                # Add the bin information to the data dictionary
                                data["bins"].append(
                                    {
                                        "type": bin_type,
                                        "collectionDate": parsed_date.strftime(
                                            date_format
                                        ),
                                    }
                                )
                            except ValueError as e:
                                print(f"Error parsing date for {bin_type}: {e}")
                        else:
                            print(f"No next collection date found for {bin_type}")
                    else:
                        print(f"No 'Next collection' text found for {bin_type}")
                else:
                    print(f"No summary list found for {bin_type}")

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
