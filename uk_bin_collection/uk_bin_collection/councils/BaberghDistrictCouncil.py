import re
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# Liferay portlet namespace used to build element ids on the page.
PORTLET_NS = (
    "_com_placecube_digitalplace_local_waste_portlet_CollectionDayFinderPortlet_"
)


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        """Scrape Babergh's collection-day finder and return bin collections.

        Drives the Selenium-based postcode/address lookup, submits the
        "Find collection days" form and parses the resulting table into a
        dict of ``{"bins": [{"type", "collectionDate"}, ...]}``.

        Args:
            page: Unused; the council requires a live Selenium session.
            **kwargs: Expects ``postcode`` and ``paon`` (house name/number),
                plus optional ``web_driver`` and ``headless`` settings.

        Returns:
            A dict with a ``bins`` list of collection type/date entries.
        """
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

            url = "https://www.babergh.gov.uk/check-your-collection-day"

            # Get our initial session running
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get(url)

            wait = WebDriverWait(driver, 30)

            # Enter postcode
            postcode_input = wait.until(
                EC.presence_of_element_located((By.ID, f"{PORTLET_NS}postcode"))
            )
            postcode_input.send_keys(user_postcode)

            # Click find address
            find_address_button = wait.until(
                EC.element_to_be_clickable((By.ID, f"{PORTLET_NS}btnAddressLookup"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", find_address_button)
            driver.execute_script("arguments[0].click();", find_address_button)

            # Wait for the address dropdown to be populated with addresses
            select_address_input = wait.until(
                EC.presence_of_element_located((By.ID, f"{PORTLET_NS}uprn"))
            )
            wait.until(lambda d: len(Select(select_address_input).options) > 1)

            # Select address based on postcode and house name/number
            select = Select(select_address_input)
            selected = False

            for addr_option in select.options:
                # Skip the placeholder option (e.g. "7 addresses found for ...")
                if not addr_option.get_attribute("value"):
                    continue

                option_text = addr_option.text.upper()
                postcode_upper = user_postcode.upper()
                paon_str = str(user_paon).upper()

                # Match the house name/number at the very start of the
                # address (options are formatted "<PAON> <STREET> <TOWN>
                # <POSTCODE>" with no separator between fields), allowing an
                # optional single-letter suffix (e.g. "1A", "1B"). Anchoring
                # to the start avoids matching it as a substring elsewhere,
                # e.g. paon "ELM COTTAGE" wrongly matching an option for
                # "THE OLD ELM COTTAGE ...".
                paon_pattern = re.compile(rf"^{re.escape(paon_str)}[A-Z]?([ ,]|$)")

                # Check if this option contains both postcode and house name/number
                if postcode_upper in option_text and paon_pattern.search(option_text):
                    select.select_by_value(addr_option.get_attribute("value"))
                    selected = True
                    break

            if not selected:
                raise ValueError(
                    f"Address not found for postcode {user_postcode} and house number {user_paon}"
                )

            # Selecting an address reveals the "Find collection days" submit
            # button; click it to load the collection day results.
            find_days_button = wait.until(
                EC.element_to_be_clickable((By.ID, f"{PORTLET_NS}fcd_submit"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", find_days_button)
            driver.execute_script("arguments[0].click();", find_days_button)

            # Wait for the results table to load. The council's own backend
            # sometimes errors for specific addresses (unrelated to this
            # scraper), rendering "Collection day finder is temporarily
            # unavailable" instead of a results table - detect that and
            # raise a clear error rather than a bare timeout.
            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.collection-days-page table")
                    )
                )
            except TimeoutException:
                if "temporarily unavailable" in driver.page_source.lower():
                    raise ValueError(
                        "Babergh's collection day finder is reporting "
                        "'temporarily unavailable' for this address - this "
                        "is an error on the council's own backend, not this "
                        "scraper. Try again later."
                    )
                raise

            # Parse the HTML content
            soup = BeautifulSoup(driver.page_source, "html.parser")

            results_page = soup.find("div", class_="collection-days-page")
            if results_page:
                table = results_page.find("table")
                if table:
                    body = table.find("tbody") or table
                    for row in body.find_all("tr"):
                        cells = row.find_all("td")
                        if len(cells) < 2:
                            continue

                        collection_type = cells[0].get_text(strip=True)
                        if not collection_type:
                            continue

                        # The "Next collection" date is in the second column;
                        # an optional "Following Collection Date" may appear in
                        # the fourth column. Capture any populated dates.
                        date_cells = [cells[1]]
                        if len(cells) >= 4:
                            date_cells.append(cells[3])

                        for date_cell in date_cells:
                            date_text = date_cell.get_text(strip=True)
                            if not date_text:
                                continue

                            # Dates are formatted like "Monday 08 Jun 2026"
                            collection_date = datetime.strptime(
                                date_text, "%A %d %b %Y"
                            )

                            dict_data = {
                                "type": collection_type,
                                "collectionDate": collection_date.strftime(date_format),
                            }
                            data["bins"].append(dict_data)

            # Fail loud if no collections were parsed. The results table was
            # present, so an empty result means the page format has changed
            # rather than there being genuinely no upcoming collections;
            # silently returning no bins would freeze downstream sensors.
            if not data["bins"]:
                raise ValueError(
                    "No bin collections found - the Babergh results page "
                    "format may have changed."
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
