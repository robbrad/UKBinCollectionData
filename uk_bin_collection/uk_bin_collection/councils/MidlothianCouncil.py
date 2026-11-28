import re
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

        driver = None
        try:
            # Prefer the stealth driver where a display exists. It used to be
            # forced non-headless, which made Chrome exit at start-up on a
            # machine with no display ("SessionNotCreatedException"); without
            # a display create_webdriver now falls back to the ordinary driver
            # and honours `headless` (the fillform iframe loads fine headless).
            driver = create_webdriver(
                web_driver, headless, None, __name__, stealth=True
            )
            driver.get(self.START_URL)

            iframe = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, self.IFRAME_ID))
            )
            driver.switch_to.frame(iframe)

            postcode_input = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.ID, "postcode"))
            )
            # The postcode field is clickable/enabled well before the form's
            # own JS finishes attaching its address-lookup handlers - typing
            # into it too early leaves #listAddress never populated (#2212).
            # There's no reliable DOM signal for "handlers attached", so
            # give the form a moment to finish initialising.
            time.sleep(2)
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
            target = self.pick_address_text(
                [opt.text for opt in select.options], house_identifier
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

            bins.sort(key=lambda x: datetime.strptime(x["collectionDate"], date_format))
            return {"bins": bins}

        finally:
            if driver:
                driver.quit()

    @staticmethod
    def pick_address_text(option_texts, house_identifier):
        """Return the one option starting with house_identifier as a whole word.

        Raises ValueError when none, or more than one, option matches.
        """
        wanted = re.escape(house_identifier.strip().upper())
        pattern = re.compile(rf"^{wanted}(?![A-Z0-9])")
        matches = [
            text.strip()
            for text in option_texts
            if text.strip()
            and not text.strip().lower().startswith("select")
            and pattern.match(text.strip().upper())
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one address starting with '{house_identifier}', "
                f"found {len(matches)}: {matches or [t.strip() for t in option_texts]}"
            )
        return matches[0]
