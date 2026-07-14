from __future__ import annotations

import datetime as dt

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        global By, EC, WebDriverWait
        from uk_bin_collection.uk_bin_collection.common import (
            ensure_selenium_dependencies,
        )

        ensure_selenium_dependencies()
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.wait import WebDriverWait

        driver = None
        try:
            data = {"bins": []}
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get(
                "https://testvalley.gov.uk/wasteandrecycling/when-are-my-bins-collected/when-are-my-bins-collected"
            )

            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "postcodeSearch"))
            )
            inputElement_postcode.send_keys(user_postcode)

            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "govuk-button"))
            )
            driver.execute_script("arguments[0].click();", findAddress)

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//select[@id='addressSelect']//option[contains(., '"
                        + user_paon
                        + "')]",
                    )
                )
            ).click()

            import time

            time.sleep(8)

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            collections = soup.find_all("div", {"class": "p-2"})

            for collection in collections:
                h3 = collection.find("h3")
                if not h3:
                    continue
                bin_type = h3.get_text(strip=True)

                bold_div = collection.find("div", {"class": "fw-bold"})
                if not bold_div:
                    continue
                next_collection_text = bold_div.get_text(strip=True)

                next_date = self._parse_date(next_collection_text)
                if next_date:
                    data["bins"].append(
                        {
                            "type": bin_type,
                            "collectionDate": next_date.strftime(date_format),
                        }
                    )

                followed_div = collection.find(
                    lambda t: (
                        t.name == "div"
                        and t.get_text(strip=True).lower().startswith("followed by")
                    )
                )
                if followed_div:
                    following_text = followed_div.get_text(strip=True)
                    following_date = self._parse_date(
                        following_text.replace("followed by ", "").replace(
                            "Followed by ", ""
                        )
                    )
                    if following_date:
                        data["bins"].append(
                            {
                                "type": bin_type,
                                "collectionDate": following_date.strftime(date_format),
                            }
                        )

        except Exception as e:
            print(f"An error occurred: {type(e).__name__}")
            raise
        finally:
            if driver:
                driver.quit()
        return data

    @staticmethod
    def _parse_date(text: str):
        import re

        text = re.sub(r"(st|nd|rd|th)", "", text).strip()
        try:
            parsed = dt.datetime.strptime(text, "%A %d %B").date()
        except ValueError:
            return None
        current_date = dt.date.today()
        parsed = parsed.replace(year=current_date.year)
        if parsed < current_date:
            parsed = parsed.replace(year=current_date.year + 1)
        return parsed
