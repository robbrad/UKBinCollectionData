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


_ORDINAL_RE = re.compile(r"(\d+)(?:st|nd|rd|th)", re.IGNORECASE)


def _strip_ordinal(date_text: str) -> str:
    return _ORDINAL_RE.sub(r"\1", date_text).strip()


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        """
        NHDC migrated from the Cloud9 `citizenmobile/mobileapi/{UPRN}` endpoint
        (now 404) to a Netcall Liberty Create portal at
        waste.nc.north-herts.gov.uk. The new flow is a typeahead search keyed
        on postcode/address, selection of a record, and a server-rendered
        result page. No public UPRN shortcut exists — submit URLs carry an
        auth signature bound to the session-issued webpage_token.

        kwargs:
            postcode (str): required.
            paon    (str): required. Matched as a case-insensitive substring
                           against the typeahead list item text.
            web_driver, headless: passed through to create_webdriver.
        """
        driver = None
        try:
            user_postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_postcode(user_postcode)
            check_paon(user_paon)

            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
            )
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get(
                "https://waste.nc.north-herts.gov.uk/w/webpage/find-bin-collection-day-input-address"
            )

            wait = WebDriverWait(driver, 30)

            # Typeahead input — Liberty's visible field uses this class
            search_input = wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "input.relation_path_type_ahead_search",
                ))
            )
            search_input.click()
            search_input.clear()
            # send_keys one char at a time so Liberty's debounced keyup fires
            for ch in user_postcode:
                search_input.send_keys(ch)
                time.sleep(0.05)
            # Nudge the debounce
            search_input.send_keys(Keys.END)

            # Wait for result list to appear and populate
            result_list_locator = (
                By.CSS_SELECTOR,
                "div.relation_path_type_ahead_results_holder ul.result_list li[data-id]",
            )
            wait.until(EC.presence_of_element_located(result_list_locator))
            # Give it another beat for all results to arrive
            time.sleep(1)

            items = driver.find_elements(*result_list_locator)
            if not items:
                raise ValueError(
                    f"NHDC typeahead returned no addresses for postcode {user_postcode}"
                )

            paon_lc = str(user_paon).lower()
            target = None
            for li in items:
                if paon_lc in li.text.lower():
                    target = li
                    break
            if target is None:
                # Fall back to the first result rather than blow up — caller
                # may have supplied just a postcode for a single-property match
                target = items[0]

            target.click()
            time.sleep(0.5)

            submit_btn = wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    'input[type="submit"][aria-label="Select address and continue"]',
                ))
            )
            submit_btn.click()

            # Wait for the result page — URL pattern ends in "show-details"
            WebDriverWait(driver, 30).until(
                lambda d: "show-details" in d.current_url
            )
            # Wait for the bin content to render
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//strong[normalize-space()='Next collection']",
                ))
            )

            soup = BeautifulSoup(driver.page_source, "html.parser")

            data = {"bins": []}

            # Liberty renders each bin type as a block containing:
            #   <h*>Cardboard & Paper</h*>
            #   <table> ... <p><strong>Next collection</strong><br>Thursday 23rd April 2026</p> ...
            # The bin type heading can be h2/h3/h4/strong depending on theme.
            # Strategy: find each <strong>Next collection</strong>, walk up to
            # the enclosing block, look back for the most recent heading text
            # naming the bin type.
            bin_type_whitelist = {
                "Cardboard & Paper",
                "Cardboard and Paper",
                "Food Waste",
                "Non-Recyclable Waste",
                "Non Recyclable Waste",
                "Garden Waste",
                "Mixed Recycling",
                "Refuse",
                "Glass",
            }

            # Collect (bin_type, date) pairs by walking the DOM order
            body_text_nodes = []
            for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "strong", "p"]):
                text = el.get_text(" ", strip=True)
                if not text:
                    continue
                body_text_nodes.append((el, text))

            current_type = None
            for el, text in body_text_nodes:
                # Match a bin-type heading
                for candidate in bin_type_whitelist:
                    if text.lower() == candidate.lower():
                        current_type = candidate.replace(" and ", " & ")
                        break
                # Match a "Next collection" block — the date is either after
                # the <br> in the same <p>, or the element's trailing text
                if "Next collection" in text and current_type:
                    # Pull the date from element text after the "Next collection" label
                    date_match = re.search(
                        r"Next collection\s+(?:on\s+)?"
                        r"([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})",
                        text,
                    )
                    if date_match:
                        raw = _strip_ordinal(date_match.group(1))
                        try:
                            parsed = datetime.strptime(raw, "%A %d %B %Y")
                        except ValueError:
                            continue
                        data["bins"].append({
                            "type": current_type,
                            "collectionDate": parsed.strftime(date_format),
                        })

            # Dedupe while preserving order
            seen = set()
            unique = []
            for b in data["bins"]:
                key = (b["type"], b["collectionDate"])
                if key in seen:
                    continue
                seen.add(key)
                unique.append(b)
            data["bins"] = unique

            data["bins"].sort(
                key=lambda x: datetime.strptime(x["collectionDate"], date_format)
            )
            return data
        finally:
            if driver is not None:
                driver.quit()
