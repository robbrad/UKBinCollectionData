import re
import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

ITV_URL = (
    "https://iportal.itouchvision.com/icollectionday/collection-day/"
    "?uuid=EDDECF9K2FVE8F52D66B1E048340100007FJ6D5C&lang=en"
)


def _parse_date(text):
    text = text.strip()
    current_year = datetime.now().year
    for fmt in ["%A %d %B", "%d %B", "%A %d %b", "%d %b"]:
        try:
            parsed = datetime.strptime(text, fmt).replace(year=current_year)
            if parsed.month < datetime.now().month - 1:
                parsed = parsed.replace(year=current_year + 1)
            return parsed
        except ValueError:
            continue
    return None


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            data = {"bins": []}

            user_postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")
            check_postcode(user_postcode)
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(ITV_URL)
            time.sleep(8)

            inp = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='text']"))
            )
            inp.clear()
            inp.send_keys(user_postcode)
            inp.send_keys(Keys.RETURN)

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "select"))
            )
            time.sleep(2)

            select = Select(driver.find_element(By.TAG_NAME, "select"))
            selected = False
            if user_paon:
                for option in select.options:
                    text = option.text.strip()
                    if text.lower().startswith(user_paon.lower()):
                        select.select_by_visible_text(text)
                        selected = True
                        break
                if not selected:
                    for option in select.options:
                        text = option.text.strip()
                        if user_paon.lower() in text.lower():
                            select.select_by_visible_text(text)
                            selected = True
                            break
            if not selected and len(select.options) > 1:
                select.select_by_index(1)

            time.sleep(8)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            collections_div = soup.find("h2", string=re.compile(r"Your next collections", re.I))
            if not collections_div:
                raise ValueError("Collection results not found on page")

            parent = collections_div.find_parent("div")
            if not parent:
                parent = collections_div.parent

            cards = parent.find_all("h3")
            for card_heading in cards:
                bin_type = card_heading.get_text(strip=True)
                card = card_heading.find_parent("div", class_=re.compile(r"ant-col|col"))
                if not card:
                    card = card_heading.find_parent("div")

                card_text = card.get_text(separator="\n", strip=True) if card else ""

                date_matches = re.findall(
                    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d{1,2}\s+\w+",
                    card_text, re.I
                )

                seen = set()
                for date_str in date_matches:
                    parsed = _parse_date(date_str)
                    if parsed:
                        cd = parsed.strftime(date_format)
                        key = (bin_type, cd)
                        if key not in seen:
                            seen.add(key)
                            data["bins"].append({
                                "type": bin_type,
                                "collectionDate": cd,
                            })

            if data["bins"]:
                data["bins"].sort(
                    key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
                )

            return data

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
