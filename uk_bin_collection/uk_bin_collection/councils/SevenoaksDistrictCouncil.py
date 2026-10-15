from bs4 import BeautifulSoup
from dateutil.parser import parse
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import create_webdriver, date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def _parse_collections(self, html: str) -> dict:
        """Extract each waste type's dates from the rendered collection cards."""
        soup = BeautifulSoup(html, "html.parser")
        data = {"bins": []}
        for card in soup.select(".gwBorderSlim"):
            heading = card.find("h2")
            if heading is None:
                continue

            # Each waste type has its own date listing. Informational text and
            # unsubscribed services have no date fragment and must be skipped.
            for date_element in card.select(
                ".system_widget_foundation_listing "
                ".page_fragment[data-current_value] .value-as-text"
            ):
                raw_date = date_element.get_text(strip=True)
                if (
                    not raw_date
                    or "suspended" in raw_date.lower()
                    or "restarting" in raw_date.lower()
                ):
                    continue
                parsed_date = parse(raw_date, dayfirst=True)
                data["bins"].append(
                    {
                        "type": heading.get_text(strip=True),
                        "collectionDate": parsed_date.strftime(date_format),
                    }
                )
        return data

    def wait_for_element_conditions(self, driver, conditions, timeout: int = 5):
        """Wait for a Selenium condition, propagating a timeout if it fails."""
        try:
            WebDriverWait(driver, timeout).until(conditions)
        except TimeoutException:
            print("Timed out waiting for page to load")
            raise

    def parse_data(self, page: str, **kwargs) -> dict:
        """Look up a postcode and address, returning their collection dates."""
        driver = None
        try:
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            page = "https://sevenoaks-dc-host01.oncreate.app/w/webpage/waste-collection-day"

            # Assign user info
            user_postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")

            # Create Selenium webdriver
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get(page)

            # Enter postcode
            postcode_css_selector = "#address_search_postcode"
            self.wait_for_element_conditions(
                driver,
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, postcode_css_selector)
                ),
            )
            postcode_input_box = driver.find_element(
                By.CSS_SELECTOR, postcode_css_selector
            )
            postcode_input_box.send_keys(user_postcode)
            postcode_input_box.send_keys(Keys.ENTER)

            # Select the dropdown
            self.wait_for_element_conditions(
                driver, EC.presence_of_element_located((By.XPATH, "//select/option[2]"))
            )
            select_address_dropdown = Select(driver.find_element(By.XPATH, "//select"))

            if user_paon is not None:
                for option in select_address_dropdown.options:
                    if user_paon in option.text:
                        select_address_dropdown.select_by_visible_text(option.text)
                        break
            else:
                # If we've not been supplied an address, pick the second entry
                select_address_dropdown.select_by_index(1)

            # Wait for the collection cards on the address details page.
            self.wait_for_element_conditions(
                driver,
                EC.presence_of_element_located((By.CSS_SELECTOR, ".gwBorderSlim h2")),
            )
            data = self._parse_collections(driver.page_source)
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
