import re
from datetime import datetime

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        check_paon(user_paon)
        check_postcode(user_postcode)

        if PLAYWRIGHT_AVAILABLE:
            return self._parse_playwright(user_postcode, user_paon)
        return self._parse_selenium(user_postcode, user_paon, kwargs)

    @staticmethod
    def _extract_bins(soup):
        data = {"bins": []}
        current_year = datetime.now().year
        cards = soup.find_all("div", class_="card")
        for card in cards:
            h3 = card.find("h3")
            if not h3:
                continue
            bin_type = h3.get_text(strip=True)
            date_span = card.find("span", class_="card__date")
            if not date_span:
                continue
            date_text = date_span.get_text(strip=True)
            match = re.search(r"(\d{2}/\d{2})(?:/(\d{4}))?", date_text)
            if match:
                day_month = match.group(1)
                year = match.group(2) or str(current_year)
                full_date = f"{day_month}/{year}"
                parsed = datetime.strptime(full_date, "%d/%m/%Y")
                if parsed.date() < datetime.now().date():
                    parsed = parsed.replace(year=current_year + 1)
                data["bins"].append({
                    "type": bin_type,
                    "collectionDate": parsed.strftime(date_format),
                })
        return data

    def _parse_playwright(self, postcode, paon):
        import time
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(
                "https://www.wokingham.gov.uk/rubbish-and-recycling/waste-collection/find-your-bin-collection-day",
                wait_until="networkidle",
                timeout=30000,
            )
            time.sleep(2)

            page.fill("#edit-postcode-search", postcode)
            page.press("#edit-postcode-search", "Enter")
            page.wait_for_selector("#edit-address-options option:nth-child(2)", state="attached", timeout=15000)

            options = page.query_selector_all("#edit-address-options option")
            paon_upper = paon.upper()
            matched = False
            for opt in options:
                text = (opt.text_content() or "").strip().upper()
                if text.startswith(paon_upper + ",") or text.startswith(paon_upper + " "):
                    page.select_option("#edit-address-options", value=opt.get_attribute("value"))
                    matched = True
                    break
            if not matched and options:
                page.select_option("#edit-address-options", index=1)

            page.click("#edit-show-collection-dates")
            page.wait_for_selector("span.card__date", timeout=15000)
            time.sleep(2)

            soup = BeautifulSoup(page.content(), "html.parser")
            browser.close()

        return self._extract_bins(soup)

    def _parse_selenium(self, postcode, paon, kwargs):
        import time
        driver = None
        try:
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get(
                "https://www.wokingham.gov.uk/rubbish-and-recycling/waste-collection/find-your-bin-collection-day"
            )
            time.sleep(2)
            driver.execute_script("document.querySelectorAll([id*=ccc],[class*=cookie]).forEach(e => e.remove());")

            inp = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "edit-postcode-search"))
            )
            inp.send_keys(postcode)
            inp.send_keys(Keys.RETURN)

            WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//select[@id=edit-address-options]//option[starts-with(normalize-space(.), {paon})]")
                )
            ).click()

            show_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "edit-show-collection-dates"))
            )
            driver.execute_script("arguments[0].click();", show_btn)

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.card__date"))
            )
            time.sleep(2)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            return self._extract_bins(soup)
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
