from __future__ import annotations

import re
import time
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        global By, EC, Select, WebDriverWait
        from uk_bin_collection.uk_bin_collection.common import (
            ensure_selenium_dependencies,
        )

        ensure_selenium_dependencies()
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import Select
        from selenium.webdriver.support.wait import WebDriverWait

        driver = None
        try:
            page = (
                "https://forms.towerhamlets.gov.uk/en/AchieveForms/"
                "?form_uri=sandbox-publish://AF-Process-7693495e-0aa2-4438-872c-2a6e5f3da446"
                "/AF-Stage-4c6e80ac-7dc2-46e4-afa6-fd46d11565ec/definition.json"
                "&redirectlink=/en&cancelRedirectLink=/en&consentMessage=yes"
            )

            user_postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_postcode(user_postcode)

            user_agent = (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            )
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get(page)

            # Switch to the AchieveForms iframe (name may be empty, match by src)
            iframe = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "iframe[src*='fillform']")
                )
            )
            driver.switch_to.frame(iframe)

            wait = WebDriverWait(driver, 60)

            # Enter postcode
            postcode_input = wait.until(
                EC.element_to_be_clickable((By.NAME, "postcodeCustomerEntry"))
            )
            postcode_input.clear()
            postcode_input.send_keys(user_postcode)
            time.sleep(1)

            # Click Find address
            find_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Find address')]")
                )
            )
            find_btn.click()

            # Wait for address dropdown to appear and populate
            address_select_el = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//select[@name='Address']",
                    )
                )
            )

            # Wait for options to load via JavaScript (avoids stale element issues)
            WebDriverWait(driver, 30).until(
                lambda d: d.execute_script(
                    "return document.querySelector('select[name=Address]')"
                    " && document.querySelector('select[name=Address]').options.length > 1"
                )
            )

            # Use JavaScript to read options and select — DOM rebuilds cause
            # stale element errors with Selenium's Select() API
            paon_lower = (user_paon or "").strip().lower()
            selected = driver.execute_script(
                """
                var sel = document.querySelector('select[name="Address"]');
                var paon = arguments[0];
                var targetIdx = -1;
                for (var i = 0; i < sel.options.length; i++) {
                    var t = sel.options[i].text.trim().toLowerCase();
                    if (t === 'select...' || t === '') continue;
                    if (paon && (t.startsWith(paon + ',') || t.startsWith(paon + ' '))) {
                        targetIdx = i; break;
                    }
                }
                if (targetIdx === -1 && paon) {
                    for (var i = 0; i < sel.options.length; i++) {
                        if (sel.options[i].text.trim().toLowerCase().indexOf(paon) >= 0) {
                            targetIdx = i; break;
                        }
                    }
                }
                if (targetIdx === -1) {
                    for (var i = 0; i < sel.options.length; i++) {
                        if (sel.options[i].text.trim().toLowerCase() !== 'select...') {
                            targetIdx = i; break;
                        }
                    }
                }
                if (targetIdx >= 0) {
                    sel.selectedIndex = targetIdx;
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                    return sel.options[targetIdx].text;
                }
                return null;
                """,
                paon_lower,
            )

            if not selected:
                raise ValueError(f"No addresses found for postcode {user_postcode}")

            time.sleep(8)

            def _field(name):
                els = driver.find_elements(By.NAME, name)
                return els[0].get_attribute("value").strip() if els else ""

            data = {"bins": []}
            today = datetime.now()

            timeband_street = _field("Timeband_street")
            am_time = _field("single_AM_Timeband") or _field("AM_Timeband1")
            pm_time = _field("single_PM_Timeband") or _field("PM_Timeband1")
            collection_day = _field("CollectionDay")
            collection_date = _field("CollectionDate")

            if timeband_street and (am_time or pm_time):
                parts = []
                if am_time:
                    parts.append(f"AM: {am_time}")
                if pm_time:
                    parts.append(f"PM: {pm_time}")
                time_info = " / ".join(parts)
                bin_type = f"Daily Collection ({time_info})"
                for i in range(7):
                    day = today + timedelta(days=i)
                    data["bins"].append(
                        {
                            "type": bin_type,
                            "collectionDate": day.strftime(date_format),
                        }
                    )
            elif collection_date:
                try:
                    dt = datetime.strptime(collection_date, "%d/%m/%Y")
                    data["bins"].append(
                        {
                            "type": _field("CollectionService") or "General Waste",
                            "collectionDate": dt.strftime(date_format),
                        }
                    )
                except ValueError:
                    pass
            elif collection_day:
                data["bins"].append(
                    {
                        "type": "General Waste",
                        "collectionDate": get_next_day_of_week(collection_day),
                    }
                )

            if not data["bins"]:
                raise ValueError(
                    f"No collection data found for {user_postcode}. "
                    "This address may have a weekly collection that is "
                    "not shown by the council's online form."
                )

            return data

        except Exception as e:
            print(f"An error occurred: {type(e).__name__}")
            raise
        finally:
            if driver:
                driver.quit()
