from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

_NS = "_com_placecube_digitalplace_local_waste_portlet_CollectionDayFinderPortlet_"


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
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            user_postcode = kwargs.get("postcode")
            if not user_postcode:
                raise ValueError("No postcode provided.")
            check_postcode(user_postcode)
            user_paon = kwargs.get("paon")
            if not user_paon:
                raise ValueError("No house name/number provided.")
            check_paon(user_paon)

            data = {"bins": []}

            url = "https://www.midsuffolk.gov.uk/check-your-collection-day"

            # Get our initial session running
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(url)

            # Enter postcode. The field no longer has an aria-label, so
            # target it by its stable namespaced id instead.
            postcode_input = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, f"{_NS}postcode"))
            )
            postcode_input.send_keys(user_postcode)

            # Click find address
            find_address_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.ID, f"{_NS}btnAddressLookup"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", find_address_button)
            driver.execute_script("arguments[0].click();", find_address_button)

            # Wait for the address dropdown to appear and populate.
            def _populated_select(d):
                try:
                    select_el = d.find_element(By.ID, f"{_NS}uprn")
                except Exception:
                    return False
                return (
                    select_el
                    if len(select_el.find_elements(By.TAG_NAME, "option")) > 1
                    else False
                )

            select_address_input = WebDriverWait(driver, 30).until(_populated_select)

            # Select address based on postcode and house number. Iterate and
            # prefer an exact-prefix match over substring matches so e.g.
            # "ANNEXE 91 THE COMMON" doesn't beat "91 THE COMMON" when the
            # caller asked for house number 91.
            select = Select(select_address_input)
            postcode_upper = user_postcode.upper()
            paon_str = str(user_paon).upper()

            best_value = None
            best_priority = 99
            for addr_option in select.options:
                if not addr_option.text or addr_option.text.strip() == "":
                    continue
                option_text = addr_option.text.upper()
                if postcode_upper not in option_text:
                    continue

                if option_text.startswith(f"{paon_str} "):
                    priority = 0
                elif (
                    f", {paon_str}," in option_text
                    or f", {paon_str} " in option_text
                    or option_text.endswith(f", {paon_str}")
                ):
                    priority = 1
                elif f", {paon_str}A," in option_text:
                    priority = 2
                elif f" {paon_str} " in option_text:
                    # Fallback substring match (e.g. "ANNEXE 91 THE COMMON").
                    priority = 3
                else:
                    continue

                if priority < best_priority:
                    best_priority = priority
                    best_value = addr_option.get_attribute("value")
                    if priority == 0:
                        break

            if best_value is None:
                raise ValueError(
                    f"Address not found for postcode {user_postcode} and house number {user_paon}"
                )
            select.select_by_value(best_value)

            submit_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.ID, f"{_NS}fcd_submit"))
            )
            driver.execute_script("arguments[0].click();", submit_button)

            # The results now render as a table (Collection type / Next
            # collection / Frequency / Following Collection Date) rather
            # than the old collection-cards layout.
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "table.table tbody tr")
                )
            )

            # Parse the HTML content
            soup = BeautifulSoup(driver.page_source, "html.parser")

            table = soup.select_one("table.table")
            if table:
                for row in table.select("tbody tr"):
                    cells = row.find_all("td")
                    if len(cells) < 2:
                        continue

                    collection_type = cells[0].get_text(strip=True)
                    date_text = cells[1].get_text(strip=True)
                    if not date_text:
                        continue

                    collection_date = datetime.strptime(date_text, "%A %d %b %Y")
                    data["bins"].append(
                        {
                            "type": collection_type,
                            "collectionDate": collection_date.strftime(date_format),
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
