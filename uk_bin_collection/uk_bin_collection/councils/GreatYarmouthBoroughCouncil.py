import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.common.keys import Keys
from datetime import datetime

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
            user_postcode = kwargs.get("postcode")
            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            url = kwargs.get("url")

            check_uprn(user_uprn)
            check_postcode(user_postcode)

            driver = create_webdriver(web_driver, headless, None, __name__)
            
            driver.get(url)

            wait = WebDriverWait(driver, 10)
            accept_cookies_button = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.NAME,
                        "acceptall",
                    )
                )
            )
            accept_cookies_button.click()

            postcode_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.ID, "WASTECOLLECTIONCALENDARV2_ADDRESS_ALSF")
                )
            )

            postcode_input.send_keys(user_postcode)
            postcode_input.send_keys(Keys.TAB + Keys.ENTER)

            time.sleep(2)
            # Wait for address box to be visible
            select_address_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.ID,
                        "WASTECOLLECTIONCALENDARV2_ADDRESS_ALML",
                    )
                )
            )
            select_address_input.click()

            # Assume select_address_input is already the dropdown <select> element
            select = Select(select_address_input)

            # Select the option with the matching UPRN
            select.select_by_value(user_uprn)
            select_address_input.click()

            select_address_input.send_keys(Keys.TAB * 2 + Keys.ENTER)

            time.sleep(5)
            # Wait for the specified div to be present
            target_div = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "WASTECOLLECTIONCALENDARV2_LOOKUP_SHOWSCHEDULE"))
            )

            soup = BeautifulSoup(driver.page_source, "html.parser")

            bin_data = {"bins": []}
            next_collections = {}  # Dictionary to store the next collection for each bin type

            bin_types = {
                "bulky": "Bulky Collection",
                "green": "Recycling",
                "black": "General Waste",
                "brown": "Garden Waste"
            }

            for div in soup.select(".collection-area"):
                img = div.select_one("img")
                detail = div.select_one(".collection-detail")
                date_text = detail.select_one("b").get_text(strip=True)

                try:
                    # Parse the date text
                    date_obj = datetime.strptime(date_text + " 2025", "%A %d %B %Y")
                    if date_obj.date() < datetime.today().date():
                        continue  # Skip past dates
                except ValueError:
                    continue

                # Determine bin type from alt or description
                description = detail.get_text(separator=" ", strip=True).lower()
                alt_text = img['alt'].lower()

                for key, name in bin_types.items():
                    if key in alt_text or key in description:
                        # Format date as dd/mm/yyyy
                        formatted_date = date_obj.strftime("%d/%m/%Y")
                        bin_entry = {
                            "type": name,
                            "collectionDate": formatted_date
                        }
                        
                        # Only keep the earliest date for each bin type
                        if name not in next_collections or date_obj < datetime.strptime(next_collections[name]["collectionDate"], "%d/%m/%Y"):
                            next_collections[name] = bin_entry
                            print(f"Found next collection for {name}: {formatted_date}")  # Debug output
                        break

            # Add the next collections to the bin_data
            bin_data["bins"] = list(next_collections.values())

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
                
        print("\nFinal bin data:")
        print(bin_data)  # Debug output
        return bin_data
