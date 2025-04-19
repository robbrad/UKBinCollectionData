from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
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
            page = "https://www.argyll-bute.gov.uk/rubbish-and-recycling/household-waste/bin-collection"

            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_uprn(user_uprn)
            check_postcode(user_postcode)
            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            # Accept cookies
            try:
                accept_cookies = WebDriverWait(driver, timeout=10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[@id='ccc-recommended-settings']")
                    )
                )
                accept_cookies.click()
            except:
                print(
                    "Accept cookies banner not found or clickable within the specified time."
                )
                pass
            # Wait for postcode entry box

            postcode_input = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@id='edit-postcode']")
                )
            )

            postcode_input.send_keys(user_postcode)

            search_btn = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located((By.ID, "edit-submit"))
            )
            search_btn.click()

            address_results = Select(
                WebDriverWait(driver, timeout=15).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//select[@id='edit-address']")
                    )
                )
            )

            address_results.select_by_value(user_uprn)
            submit_btn = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@value='Search for my bin collection details']")
                )
            )
            submit_btn.click()

            results = WebDriverWait(driver, timeout=15).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//th[contains(text(),'Collection date')]/ancestor::table",
                    )
                )
            )

            soup = BeautifulSoup(
                results.get_attribute("innerHTML"), features="html.parser"
            )

            today = datetime.today()
            current_year = today.year
            current_month = today.month

            bin_data = {"bins": []}

            # Skip header
            for row in soup.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue

                bin_type = cells[0].get_text(strip=True)
                raw_date = cells[1].get_text(strip=True)

                try:
                    # Parse day and month first to determine year
                    partial_date = datetime.strptime(raw_date, "%A %d %B")
                    month = partial_date.month

                    # Determine correct year based on current month
                    year = current_year + 1 if month < current_month else current_year

                    # Re-parse with the correct year
                    full_date_str = f"{raw_date} {year}"
                    parsed_date = datetime.strptime(full_date_str, "%A %d %B %Y")
                    date_str = parsed_date.strftime(date_format)
                except ValueError:
                    continue

                bin_data["bins"].append({"type": bin_type, "collectionDate": date_str})

            # Sort by date
            bin_data["bins"].sort(
                key=lambda x: datetime.strptime(x["collectionDate"], date_format)
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
        return bin_data
