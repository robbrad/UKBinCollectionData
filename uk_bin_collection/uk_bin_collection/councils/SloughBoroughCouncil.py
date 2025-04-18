import re
import time

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException  # Add this line
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

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
        bin_data = {"bins": []}  # Initialize bin_data to store bin collection details
        try:
            user_paon = kwargs.get("paon")
            check_paon(user_paon)
            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            driver = create_webdriver(web_driver, headless, None, __name__)
            page = "https://www.slough.gov.uk/directory/25/a-to-z/A"

            driver.get(page)

            wait = WebDriverWait(driver, 10)
            accept_cookies_button = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//*[@id='ccc-recommended-settings']",
                    )
                )
            )
            accept_cookies_button.click()

            # Extract the first letter of user_paon
            first_letter = user_paon[
                0
            ].upper()  # Convert to uppercase to match the HTML

            # Locate the corresponding button or link for the first letter
            try:
                letter_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//span[text()='{first_letter}']/ancestor::a")
                    )
                )
                # Scroll to the element (if necessary) and click it
                driver.execute_script("arguments[0].scrollIntoView();", letter_button)
                letter_button.click()
            except TimeoutException:
                print(f"Letter '{first_letter}' is not clickable or not found.")

            # Wait for the page to load and locate the list of streets
            try:
                street_list = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "list--record"))
                )

                # Extract the street name from user_paon
                street_name = user_paon.strip()

                # Locate the corresponding street link
                street_link = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            f"//span[contains(text(), '{street_name}')]/ancestor::a",
                        )
                    )
                )

                # Scroll to the element (if necessary) and click it
                driver.execute_script("arguments[0].scrollIntoView();", street_link)
                street_link.click()
            except TimeoutException:
                print(f"Street '{street_name}' is not clickable or not found.")

            # Wait for the page to load after clicking the street name
            try:
                # Wait for the table to appear on the next page
                table_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "list--definition"))
                )

                # Parse the page source with BeautifulSoup
                soup = BeautifulSoup(driver.page_source, "html.parser")

                # Find the definition list (dl) element
                definition_list = soup.find("dl", class_="list--definition")
                if not definition_list:
                    raise Exception("Definition list not found on the page.")

                # Iterate through all <dt> and <dd> pairs in the <dl> element
                for dt, dd in zip(
                    definition_list.find_all("dt"), definition_list.find_all("dd")
                ):
                    heading = dt.text.strip()
                    content = dd.text.strip()

                    # Use a regular expression to match "<colour> Bin"
                    match = re.match(r"(\w+)\s+Bin", heading, re.IGNORECASE)
                    if match:
                        bin_type = match.group(
                            0
                        )  # Get the full match (e.g., "Grey Bin")

                        # Remove the bin name from the collection date
                        cleaned_content = re.sub(
                            r"\s*-\s*\w+\s+bin.*$", "", content, flags=re.IGNORECASE
                        )

                        bin_data["bins"].append(
                            {
                                "type": bin_type,
                                "collectionDate": cleaned_content,
                            }
                        )

                # Debugging: Log the final bin_data
                print(f"Final bin_data: {bin_data}")

            except TimeoutException:
                print("The table with bin collection details was not found.")

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()

        return bin_data
