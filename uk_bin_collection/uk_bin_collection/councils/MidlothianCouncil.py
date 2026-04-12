import time
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Midlothian Council — Granicus / MyMidlothian self-service portal.

    The bin collection service is now a "fillform" iframe at
    my.midlothian.gov.uk. Typing a postcode auto-populates the
    #listAddress dropdown, and selecting an address auto-fills the
    per-bin date fields (dateCard, dateFood, dateGarden, dateGlass,
    dateRecycling, dateResidual). No submit step needed.
    """

    START_URL = "https://my.midlothian.gov.uk/service/Bin_Collection_Dates"
    IFRAME_ID = "fillform-frame-1"

    # Field id -> human-readable bin type
    DATE_FIELDS = {
        "dateResidual": "General waste",
        "dateRecycling": "Recycling",
        "dateFood": "Food waste",
        "dateGarden": "Garden waste",
        "dateGlass": "Glass",
        "dateCard": "Cardboard",
    }

    def parse_data(self, page: str, **kwargs) -> dict:
        house_identifier = (kwargs.get("paon") or kwargs.get("number") or "").strip()
        user_postcode = kwargs.get("postcode")
        web_driver = kwargs.get("web_driver")
        headless = kwargs.get("headless")

        if not house_identifier:
            raise ValueError("Midlothian requires a house identifier (-n / --number)")
        if not user_postcode:
            raise ValueError("Midlothian requires a postcode (-p / --postcode)")

        check_postcode(user_postcode)

        # The fillform iframe blocks headless Chrome AND vanilla Selenium
        # (the bot-detection scripts check for navigator.webdriver). Use
        # undetected_chromedriver in non-headless mode via the Xvfb display
        # available on the VPS.
        import os
        driver = None
        try:
            if os.environ.get("DISPLAY") and web_driver is None:
                try:
                    import undetected_chromedriver as uc
                    uc_opts = uc.ChromeOptions()
                    uc_opts.add_argument("--no-sandbox")
                    uc_opts.add_argument("--disable-dev-shm-usage")
                    uc_opts.add_argument("--window-size=1920,1080")
                    driver = uc.Chrome(options=uc_opts, version_main=146)
                except Exception:
                    driver = None
            if driver is None:
                driver = create_webdriver(web_driver, False, None, __name__)
            driver.get(self.START_URL)

            iframe = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, self.IFRAME_ID))
            )
            driver.switch_to.frame(iframe)

            postcode_input = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.ID, "postcode"))
            )
            postcode_input.clear()
            postcode_input.send_keys(user_postcode)

            def dropdown_populated(d):
                try:
                    sel = d.find_element(By.ID, "listAddress")
                    return len(sel.find_elements(By.TAG_NAME, "option")) > 1
                except Exception:
                    return False

            WebDriverWait(driver, 30).until(dropdown_populated)

            select = Select(driver.find_element(By.ID, "listAddress"))
            target = self._pick_address_option(select, house_identifier)
            if target is None:
                raise Exception(
                    f"Could not find address '{house_identifier}' in options: "
                    f"{[o.text.strip() for o in select.options]}"
                )
            select.select_by_visible_text(target)

            # Give the form time to pull the per-bin dates down.
            WebDriverWait(driver, 30).until(
                lambda d: (
                    d.find_element(By.ID, "dateResidual").get_attribute("value")
                    or d.find_element(By.ID, "dateRecycling").get_attribute("value")
                    or d.find_element(By.ID, "dateFood").get_attribute("value")
                )
            )
            time.sleep(1)

            bins = []
            for field_id, bin_type in self.DATE_FIELDS.items():
                try:
                    value = driver.find_element(By.ID, field_id).get_attribute("value")
                except Exception:
                    continue
                if not value:
                    continue
                raw = value.strip()
                try:
                    parsed = datetime.strptime(raw, "%d/%m/%Y")
                except ValueError:
                    continue
                bins.append(
                    {
                        "type": bin_type,
                        "collectionDate": parsed.strftime(date_format),
                    }
                )

            bins.sort(
                key=lambda x: datetime.strptime(x["collectionDate"], date_format)
            )
            return {"bins": bins}

        finally:
            if driver:
                driver.quit()

    @staticmethod
    def _pick_address_option(select, house_identifier):
        target = house_identifier.upper().strip()
        for opt in select.options:
            text = opt.text.strip()
            if not text or text.lower().startswith("select"):
                continue
            up = text.upper()
            if up.startswith(f"{target} ") or up.startswith(f"{target},"):
                return text
        for opt in select.options:
            text = opt.text.strip()
            if target in text.upper():
                return text
        return None
