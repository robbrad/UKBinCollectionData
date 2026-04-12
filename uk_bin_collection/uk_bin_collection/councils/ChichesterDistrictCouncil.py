import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    NoSuchElementException,
)

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

date_format = "%d/%m/%Y"


class CouncilClass(AbstractGetBinDataClass):
    """
    Chichester District Council — AchieveForms V7 at chichester.gov.uk/checkyourbinday.

    The page is protected by Cloudflare Turnstile, so callers must run this via
    a non-headless undetected-chromedriver session (the ukbcd-wrapper-uc.py
    wrapper on the VPS handles that).

    After selecting an address from the dropdown, the form loads the next
    collection dates inline in .gi-summary-blocklist__row elements — no
    separate NEXT/submit step is needed.
    """

    POSTCODE_ID = "WASTECOLLECTIONCALENDARV7_CALENDAR_ADDRESSLOOKUPPOSTCODE"
    SEARCH_ID = "WASTECOLLECTIONCALENDARV7_CALENDAR_ADDRESSLOOKUPSEARCH"
    DROPDOWN_ID = "WASTECOLLECTIONCALENDARV7_CALENDAR_ADDRESSLOOKUPADDRESS"

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            start_url = "https://www.chichester.gov.uk/checkyourbinday"

            user_postcode = kwargs.get("postcode")
            house_number = kwargs.get("paon") or kwargs.get("number")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            user_agent = (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            )
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get(start_url)

            self._wait_for_cloudflare(driver)
            self._dismiss_cookie_banner(driver)

            wait = WebDriverWait(driver, 60)

            input_postcode = wait.until(
                EC.visibility_of_element_located((By.ID, self.POSTCODE_ID))
            )
            input_postcode.clear()
            input_postcode.send_keys(user_postcode)

            search_button = wait.until(
                EC.element_to_be_clickable((By.ID, self.SEARCH_ID))
            )
            search_button.send_keys(Keys.ENTER)

            self._select_address(driver, house_number)

            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.gi-summary-blocklist__row")
                )
            )
            # Allow any remaining rows to render before parsing.
            time.sleep(1)

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            rows = soup.select("div.gi-summary-blocklist__row")

            bin_collection_data = []
            for row in rows:
                key = row.select_one("div.gi-summary-blocklist__key")
                value = row.select_one("div.gi-summary-blocklist__value")
                if not key or not value:
                    continue

                bin_type = key.get_text(strip=True)
                date_text = " ".join(value.get_text(" ", strip=True).split())

                try:
                    parsed = datetime.strptime(date_text, "%A %d %B %Y")
                except ValueError:
                    continue

                bin_collection_data.append(
                    {
                        "collectionDate": parsed.strftime(date_format),
                        "type": bin_type,
                    }
                )

            bin_collection_data.sort(
                key=lambda x: datetime.strptime(x["collectionDate"], date_format)
            )

            return {"bins": bin_collection_data}

        finally:
            if driver:
                driver.quit()

    def _wait_for_cloudflare(self, driver):
        for _ in range(25):
            title = driver.title or ""
            if "Just a moment" not in title and "Attention" not in title:
                return
            time.sleep(2)

    def _dismiss_cookie_banner(self, driver):
        for xpath in (
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),'accept')]",
            "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),'accept')]",
        ):
            try:
                btn = driver.find_element(By.XPATH, xpath)
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1)
                return
            except NoSuchElementException:
                continue
            except Exception:
                continue

    def _select_address(self, driver, house_number: str):
        if not house_number:
            raise ValueError(
                "Chichester requires a house number/name via -n / --number"
            )

        def dropdown_has_addresses(d):
            try:
                sel = d.find_element(By.ID, self.DROPDOWN_ID)
                return len(sel.find_elements(By.TAG_NAME, "option")) > 1
            except (StaleElementReferenceException, NoSuchElementException):
                return False

        WebDriverWait(driver, 45).until(dropdown_has_addresses)

        sel_element = driver.find_element(By.ID, self.DROPDOWN_ID)
        select = Select(sel_element)

        target_text = self._pick_option(select.options, house_number)
        if target_text is None:
            all_opts = [opt.text.strip() for opt in select.options]
            raise Exception(
                f"Could not find address '{house_number}' in options: {all_opts}"
            )

        for attempt in range(3):
            try:
                select.select_by_visible_text(target_text)
                return
            except StaleElementReferenceException:
                time.sleep(1)
                sel_element = driver.find_element(By.ID, self.DROPDOWN_ID)
                select = Select(sel_element)

        raise Exception(
            f"Failed to select '{target_text}' after retries"
        )

    @staticmethod
    def _pick_option(options, house_number: str):
        target = house_number.lower().strip()
        # Strict: exact match or "<target>," / "<target> " prefix
        for opt in options:
            text = opt.text.strip()
            low = text.lower()
            if low == target or low.startswith(f"{target},") or low.startswith(
                f"{target} "
            ):
                return text
        # Fuzzy: substring match
        for opt in options:
            text = opt.text.strip()
            if target in text.lower():
                return text
        return None
