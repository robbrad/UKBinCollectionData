from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            page = "https://www.wirral.gov.uk/bins-and-recycling/bin-collection-dates"
            user_postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            # Handle cookie consent if present
            try:
                cookie_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.ID, "ccc-recommended-settings")
                    )
                )
                cookie_button.click()
                time.sleep(1)
            except:
                pass  # Cookie banner not present or already accepted

            # Wait for and switch to the iframe
            iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "BinIFrame"))
            )
            driver.switch_to.frame(iframe)

            # Wait for postcode input and enter postcode
            postcode_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "MainContent_Postcode"))
            )
            postcode_input.send_keys(user_postcode)

            # Click the Go button to search for addresses
            go_button = driver.find_element(By.ID, "MainContent_LookupPostcode")
            go_button.click()

            # Wait for address dropdown to appear
            address_dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "MainContent_addressDropDown"))
            )

            # Select the address from dropdown
            select = Select(address_dropdown)
            found = False
            for option in select.options:
                if user_paon.lower() in option.text.lower():
                    option.click()
                    found = True
                    break

            if not found:
                raise ValueError(
                    f"Address with house number '{user_paon}' not found in dropdown"
                )

            # Click Find bin collections button
            find_button = driver.find_element(By.ID, "MainContent_FindRounds")
            find_button.click()

            # Wait for results to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "MainContent_MainOutput"))
            )

            # Get the page source and parse with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Extract bin collection data from the MainOutput div
            main_output = soup.find("div", {"id": "MainContent_MainOutput"})
            if not main_output:
                raise ValueError("Could not find collection data on page")

            bindata = {"bins": []}

            # Parse the text content
            text = main_output.get_text()

            # Extract Grey bin (recycling) dates
            grey_match = re.search(
                r"Grey bin.*?(\d{1,2}\s+\w+\s+\d{4})", text, re.DOTALL
            )
            if grey_match:
                date_str = grey_match.group(1)
                collection_date = datetime.strptime(date_str, "%d %B %Y").strftime(
                    date_format
                )
                bindata["bins"].append(
                    {"type": "Grey bin (recycling)", "collectionDate": collection_date}
                )

            # Extract Green bin (non-recyclable waste) dates
            green_match = re.search(
                r"Green bin.*?(\d{1,2}\s+\w+\s+\d{4})", text, re.DOTALL
            )
            if green_match:
                date_str = green_match.group(1)
                collection_date = datetime.strptime(date_str, "%d %B %Y").strftime(
                    date_format
                )
                bindata["bins"].append(
                    {
                        "type": "Green bin (non-recyclable waste)",
                        "collectionDate": collection_date,
                    }
                )

            # Sort by collection date
            bindata["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
            )

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            # Close the driver
            if driver:
                driver.quit()

        return bindata
