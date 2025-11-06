import re
import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import (
    check_postcode,
    check_uprn,
    create_webdriver,
    date_format,
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Tendring District Council scraper.

    Fix: select the 'Next collection' column (not 'Previous Collection'), and
    handle cookie banner / iframe flow robustly.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        bin_data: dict[str, list[dict]] = {"bins": []}

        try:
            # Always use the canonical service URL
            page = (
                "https://tendring-self.achieveservice.com/en/service/"
                "Rubbish_and_recycling_collection_days"
            )

            # Inputs provided by HA / CLI
            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            # Validate inputs
            check_uprn(user_uprn)
            check_postcode(user_postcode)

            # Create and launch Selenium (remote or local depending on config)
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            # Try to accept the cookie banner if present
            try:
                cookies_button = WebDriverWait(driver, timeout=15).until(
                    EC.presence_of_element_located((By.ID, "close-cookie-message"))
                )
                cookies_button.click()
            except Exception:
                # Banner not present or already dismissed — fine
                pass

            # Click "continue without an account"
            without_login_button = WebDriverWait(driver, timeout=20).until(
                EC.presence_of_element_located(
                    (By.LINK_TEXT, "or, continue without an account")
                )
            )
            without_login_button.click()

            # Switch into the embedded form iframe
            iframe = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "fillform-frame-1"))
            )
            driver.switch_to.frame(iframe)

            wait = WebDriverWait(driver, 60)

            # Enter postcode, allow addresses to populate
            input_postcode = wait.until(
                EC.element_to_be_clickable((By.NAME, "postcode_search"))
            )
            input_postcode.clear()
            input_postcode.send_keys(user_postcode)
            time.sleep(1.5)  # allow list to populate

            # Select address by UPRN
            dropdown = wait.until(
                EC.element_to_be_clickable((By.NAME, "selectAddress"))
            )
            Select(dropdown).select_by_value(str(user_uprn))

            # Wait for results table
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "wasteTable"))
            )

            # Parse HTML
            soup = BeautifulSoup(driver.page_source, "html.parser")
            table = soup.find("table", {"class": "wasteTable"})
            if not table:
                return bin_data

            # Map headers (case-insensitive)
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]

            # Find 'Next collection' column; fallback to index 2
            next_idx = None
            for i, h in enumerate(headers):
                if "next" in h and "collect" in h:
                    next_idx = i
                    break
            if next_idx is None:
                next_idx = 2  # typical order: type, previous, next

            # Waste type column (usually first)
            type_idx = 0
            for i, h in enumerate(headers):
                if "waste" in h and "type" in h:
                    type_idx = i
                    break

            rows = (table.find("tbody") or table).find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if not cols or len(cols) <= max(type_idx, next_idx):
                    continue

                # Normalise bin type (strip parentheses)
                bin_type = re.sub(
                    r"\([^)]*\)", "", cols[type_idx].get_text(strip=True)
                )

                # Extract a dd/mm/YYYY from the 'Next collection' cell
                cell_txt = cols[next_idx].get_text(" ", strip=True)
                m = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", cell_txt)
                if not m:
                    continue
                date_str = m.group(1)

                # Canonicalise date -> date_format
                try:
                    parsed = datetime.strptime(date_str, "%d/%m/%Y")
                except ValueError:
                    continue

                bin_data["bins"].append(
                    {"type": bin_type, "collectionDate": parsed.strftime(date_format)}
                )

            # Sort ascending by date
            bin_data["bins"].sort(
                key=lambda x: datetime.strptime(x["collectionDate"], "%d/%m/%Y")
            )
            return bin_data

        finally:
            if driver:
                driver.quit()
