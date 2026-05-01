import re
import time
from datetime import timedelta

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

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
            data = {"bins": []}

            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)

            # North Norfolk moved to X-Forms platform
            driver.get(
                "https://forms.north-norfolk.gov.uk/xforms/Launch/New/BinDaysJourney"
            )

            # Wait for page to fully load
            time.sleep(5)
            wait = WebDriverWait(driver, 30)

            # Landing page: tick confirm checkbox
            confirm = driver.find_element(By.ID, "Confirm")
            confirm.click()
            time.sleep(1)

            # Bypass Turnstile by unhiding the Next button group via JS
            driver.execute_script(
                "var el = document.querySelector('.NextButtonGroup');"
                "if (el) { el.hidden = false; el.style.display = 'block'; }"
            )
            time.sleep(1)

            # Click Next/Start to get to address page
            next_btn = driver.find_element(By.ID, "NextButton")
            next_btn.click()

            # Wait for postcode search field
            postcode_input = wait.until(
                EC.presence_of_element_located((By.ID, "SearchPostcode"))
            )
            postcode_input.send_keys(user_postcode)

            # Click search button
            search_btn = wait.until(
                EC.element_to_be_clickable((By.ID, "LoadAddresses"))
            )
            search_btn.click()

            # Wait for address dropdown to populate
            time.sleep(5)
            address_dropdown = driver.find_element(By.ID, "Address")

            # Select matching address
            address_select = Select(address_dropdown)
            matching_options = [
                o
                for o in address_select.options
                if user_paon.lower() in o.text.lower()
            ]
            if not matching_options:
                raise ValueError(
                    f"No matching address for '{user_paon}' in postcode {user_postcode}"
                )

            matching_options[0].click()

            # Click Select Address button
            select_addr_btn = driver.find_element(By.ID, "SelectAddress")
            select_addr_btn.click()
            time.sleep(2)

            # Click Next to get bin results
            next_btn2 = wait.until(
                EC.element_to_be_clickable((By.ID, "NextButton"))
            )
            next_btn2.click()

            # Wait for results page
            time.sleep(8)

            # Parse the results
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            page_text = soup.get_text()

            # Extract bin types and dates from text like:
            # "Your next Green bin collection is Friday 10 April"
            results = re.findall(
                r"Your next (\w[\w ]*?) bin collection is ([A-Za-z]+ \d{1,2} [A-Za-z]+)",
                page_text,
            )
            if results:
                current_year = datetime.now().year
                for result in results:
                    bin_type = result[0].strip()
                    date_str = result[1].strip()
                    try:
                        collection_date = datetime.strptime(
                            date_str + " " + str(current_year),
                            "%A %d %B %Y",
                        )
                        # Handle year rollover
                        if collection_date < datetime.now() - timedelta(days=7):
                            collection_date = collection_date.replace(
                                year=current_year + 1
                            )
                        dict_data = {
                            "type": bin_type + " bin",
                            "collectionDate": collection_date.strftime(date_format),
                        }
                        data["bins"].append(dict_data)
                    except ValueError:
                        continue

                data["bins"].sort(
                    key=lambda x: datetime.strptime(
                        x.get("collectionDate"), date_format
                    )
                )
            else:
                raise ValueError("No bin collection data found on the results page.")

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        return data
