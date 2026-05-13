import time
import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

_BIN_TYPES = {
    "180 litre refuse", "black recycling box", "blue bag", "white bag",
    "outdoor food caddy", "indoor food caddy", "garden waste",
    "240 litre refuse", "recycling box", "food caddy",
}


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            page = "https://community.fdean.gov.uk/s/waste-collection-enquiry"
            data = {"bins": []}

            house_number = kwargs.get("paon")
            postcode = kwargs.get("postcode")
            if house_number and postcode and postcode.upper() not in house_number.upper():
                full_address = f"{house_number}, {postcode}"
            else:
                full_address = house_number or postcode or ""
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get(page)

            wait = WebDriverWait(driver, 60)
            time.sleep(8)

            address_entry_field = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@role='combobox']")
                )
            )

            address_entry_field.click()
            time.sleep(1)
            address_entry_field.send_keys(str(full_address))
            time.sleep(4)

            wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//li[@role='presentation']")
                )
            )
            all_opts = driver.find_elements(By.XPATH, "//li[@role='presentation']")
            if len(all_opts) > 1:
                all_opts[-1].click()
            else:
                all_opts[0].click()
            time.sleep(2)

            next_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Next')]")
                )
            )
            driver.execute_script("arguments[0].click();", next_button)

            for _ in range(8):
                time.sleep(5)
                if driver.find_elements(By.XPATH, "//*[contains(text(), 'Collection day')]"):
                    break

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            today = datetime.now()
            current_year = today.year
            rows = soup.find_all("tr", class_="slds-hint-parent")

            if rows:
                for row in rows:
                    try:
                        th = row.find("th")
                        td = row.find("td")
                        if not th or not td:
                            continue
                        container_type = (
                            th.get("data-cell-value", "").strip()
                            or th.get_text(strip=True)
                        )
                        raw_date = (
                            td.get("data-cell-value", "").strip()
                            or td.get_text(strip=True)
                        )
                        if container_type and raw_date:
                            data["bins"].append({
                                "type": container_type,
                                "collectionDate": self._parse_date(raw_date, current_year),
                            })
                    except Exception:
                        continue
            else:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                lines = [l.strip() for l in body_text.split("\n") if l.strip()]
                for i, line in enumerate(lines):
                    if line.lower() in _BIN_TYPES and i + 1 < len(lines):
                        raw_date = lines[i + 1]
                        if self._looks_like_date(raw_date):
                            data["bins"].append({
                                "type": line,
                                "collectionDate": self._parse_date(raw_date, current_year),
                            })

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        return data

    @staticmethod
    def _looks_like_date(text):
        t = text.lower().strip()
        return t in ("today", "tomorrow") or bool(re.match(r"^(mon|tue|wed|thu|fri|sat|sun)", t))

    @staticmethod
    def _parse_date(raw_date, current_year):
        t = raw_date.lower().strip()
        if t == "today":
            return datetime.now().strftime(date_format)
        if t == "tomorrow":
            return (datetime.now() + timedelta(days=1)).strftime(date_format)
        cleaned = re.sub(r"[^\w\s,]", "", raw_date)
        parsed = datetime.strptime(cleaned, "%a, %d %B")
        parsed = parsed.replace(year=current_year)
        if parsed < datetime.now():
            parsed = parsed.replace(year=current_year + 1)
        return parsed.strftime(date_format)
