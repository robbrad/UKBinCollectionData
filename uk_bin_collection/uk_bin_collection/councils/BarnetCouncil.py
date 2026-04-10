import re
import time
from datetime import datetime

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
            user_postcode = kwargs.get("postcode")
            if not user_postcode:
                raise ValueError("No postcode provided.")
            check_postcode(user_postcode)

            user_paon = kwargs.get("paon")
            check_paon(user_paon)
            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)

            # Go directly to the Jadu form
            driver.get(
                "https://myforms.barnet.gov.uk/homepage/11/find-your-bin-collection-day"
            )

            wait = WebDriverWait(driver, 20)

            # Enter postcode
            postcode_input = wait.until(
                EC.presence_of_element_located((By.ID, "bin_collection_postcode"))
            )
            postcode_input.clear()
            postcode_input.send_keys(user_postcode)

            # Click Find button
            find_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Find')]")
                )
            )
            find_button.click()

            # Wait for address dropdown
            address_select = wait.until(
                EC.presence_of_element_located((By.ID, "bin_collection_address"))
            )
            WebDriverWait(driver, 15).until(
                lambda d: len(
                    d.find_element(By.ID, "bin_collection_address").find_elements(
                        By.TAG_NAME, "option"
                    )
                )
                > 1
            )

            # Select address matching house number
            dropdown = Select(address_select)
            selected = False
            paon_str = str(user_paon).upper().strip()

            for option in dropdown.options:
                option_text = option.text.upper().strip()
                # Match patterns like "26A Church Hill Road" or "Flat 1, 26A..."
                if paon_str in option_text:
                    # More precise: check it starts with the paon or has it after comma
                    if (
                        option_text.startswith(paon_str + " ")
                        or option_text.startswith(paon_str + ",")
                        or f", {paon_str} " in option_text
                        or f", {paon_str}," in option_text
                    ):
                        dropdown.select_by_value(option.get_attribute("value"))
                        selected = True
                        break

            if not selected:
                # Fallback: select first option containing the paon
                for option in dropdown.options:
                    if paon_str in option.text.upper():
                        dropdown.select_by_value(option.get_attribute("value"))
                        selected = True
                        break

            if not selected:
                raise ValueError(
                    f"Address not found for postcode {user_postcode} and house number {user_paon}"
                )

            # Click Find again to get results
            find_button2 = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Find')]")
                )
            )
            find_button2.click()

            # Wait for bin collection results
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul.bin-collections"))
            )

            time.sleep(2)

            # Parse results
            soup = BeautifulSoup(driver.page_source, "html.parser")
            bin_data = {"bins": []}
            current_date = datetime.now()

            collection_items = soup.select("li.bin-collection")
            for item in collection_items:
                try:
                    heading = item.select_one(".bin-collection__heading")
                    date_el = item.select_one(".bin-collection__date")

                    if heading and date_el:
                        bin_type = heading.get_text(strip=True)
                        date_text = date_el.get_text(strip=True).strip()

                        # Remove ordinal suffixes (1st, 2nd, 3rd, 4th, etc.)
                        date_text = re.sub(
                            r"(\d+)(st|nd|rd|th)", r"\1", date_text
                        )

                        # Parse "Monday, 6 April"
                        try:
                            parsed_date = datetime.strptime(
                                date_text + f" {current_date.year}",
                                "%A, %d %B %Y",
                            )
                            if parsed_date.date() < current_date.date():
                                parsed_date = parsed_date.replace(
                                    year=current_date.year + 1
                                )
                        except ValueError:
                            # Try alternative format
                            parsed_date = datetime.strptime(
                                date_text + f" {current_date.year}",
                                "%A %d %B %Y",
                            )
                            if parsed_date.date() < current_date.date():
                                parsed_date = parsed_date.replace(
                                    year=current_date.year + 1
                                )

                        bin_data["bins"].append(
                            {
                                "type": bin_type,
                                "collectionDate": parsed_date.strftime(date_format),
                            }
                        )
                except Exception:
                    continue

            if not bin_data["bins"]:
                raise ValueError("No bin data found.")

            return bin_data

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
