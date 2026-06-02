import re
import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        check_paon(user_paon)
        check_postcode(user_postcode)

        web_driver = kwargs.get("web_driver")
        headless = kwargs.get("headless")
        user_agent = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        )
        driver = create_webdriver(web_driver, headless, user_agent, __name__)
        try:
            driver.get(
                "https://www.wokingham.gov.uk/rubbish-and-recycling/"
                "waste-collection/find-your-bin-collection-day"
            )
            time.sleep(2)

            # Remove cookie overlays that intercept clicks
            driver.execute_script(
                "document.querySelectorAll('[id*=ccc],[class*=cookie]')"
                ".forEach(e => e.remove());"
            )

            inp = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "edit-postcode-search"))
            )
            inp.send_keys(user_postcode)
            inp.send_keys(Keys.RETURN)

            # Wait for address dropdown to populate
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#edit-address-options option:nth-child(2)")
                )
            )

            # Match address by house number
            options = driver.find_elements(
                By.CSS_SELECTOR, "#edit-address-options option"
            )
            paon_upper = user_paon.upper()
            matched = False
            for opt in options:
                text = opt.text.strip().upper()
                if text.startswith(paon_upper + ",") or text.startswith(
                    paon_upper + " "
                ):
                    opt.click()
                    matched = True
                    break
            if not matched and options:
                options[1].click()

            show_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "edit-show-collection-dates"))
            )
            driver.execute_script("arguments[0].click();", show_btn)

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.card__date"))
            )
            time.sleep(2)

            soup = BeautifulSoup(driver.page_source, "html.parser")
        finally:
            driver.quit()

        return self._extract_bins(soup)

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
