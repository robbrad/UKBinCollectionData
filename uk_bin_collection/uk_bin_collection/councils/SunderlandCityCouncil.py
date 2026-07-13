import platform
import re
import subprocess
import time
from datetime import datetime

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import (
    check_paon,
    check_postcode,
    date_format,
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def _installed_chrome_major_version() -> int | None:
    """
    undetected-chromedriver's own auto-detection sometimes grabs the
    latest chromedriver release instead of one matching the locally
    installed Chrome, causing a version-mismatch failure. Asking the
    local Chrome binary directly is more reliable.
    """
    exe = uc.find_chrome_executable()
    if not exe:
        return None

    if platform.system() == "Windows":
        # On Windows, `chrome.exe --version` launches the browser rather
        # than printing to stdout and returning, so read the file's
        # version resource instead.
        try:
            output = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"(Get-Item '{exe}').VersionInfo.FileVersion",
                ],
                stderr=subprocess.DEVNULL,
                timeout=10,
            ).decode()
        except Exception:
            return None
    else:
        try:
            output = subprocess.check_output(
                [exe, "--version"], stderr=subprocess.DEVNULL, timeout=10
            ).decode()
        except Exception:
            return None

    match = re.search(r"(\d+)\.", output)
    return int(match.group(1)) if match else None


class CouncilClass(AbstractGetBinDataClass):
    """
    Sunderland City Council moved its bin-day checker onto a GOSS iCM form
    behind Cloudflare bot management. Plain Selenium (headless or not,
    local or remote grid, fully stealthed) is reliably blocked - only a
    genuine, local, non-headless Chrome driven by undetected-chromedriver
    clears the challenge. That means this council cannot use the shared
    remote-grid `web_driver` pattern the other scrapers use: it always
    launches its own local, visible Chrome (e.g. under Xvfb on Linux).
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            check_paon(user_paon)
            check_postcode(user_postcode)

            options = uc.ChromeOptions()
            driver = uc.Chrome(
                options=options,
                headless=False,
                version_main=_installed_chrome_major_version(),
            )

            driver.get(
                "https://www.sunderland.gov.uk/article/12142/Find-your-bin-collection-day"
            )

            try:
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(., 'Accept all')]")
                    )
                ).click()
            except Exception:
                pass

            postcode_input = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.ID, "BINCOLLECTIONCHECKERNEWV3_ADDRESSSEARCH_SCCPOSTCODE")
                )
            )
            postcode_input.send_keys(user_postcode)
            driver.find_element(
                By.ID, "BINCOLLECTIONCHECKERNEWV3_ADDRESSSEARCH_POSTCODETRIGGER_NEXT"
            ).click()

            address_select = Select(
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (
                            By.ID,
                            "BINCOLLECTIONCHECKERNEWV3_ADDRESSSEARCH_SCCLISTOFADDRESSES",
                        )
                    )
                )
            )
            paon_upper = user_paon.strip().upper()
            matched_value = None
            for option in address_select.options:
                if option.text.strip().upper().startswith(paon_upper):
                    matched_value = option.get_attribute("value")
                    break
            if not matched_value:
                raise ValueError(f"Address not found in dropdown: {user_paon}")
            address_select.select_by_value(matched_value)

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".myaccount-block__item--bin")
                )
            )
            # The result grid renders its bin blocks (waste, recycling,
            # garden) in separate async steps with no reliable DOM signal
            # for "all done" - a fixed settle delay is more reliable here
            # than polling, since slower blocks (e.g. Garden Waste) can
            # still be mid-render when a stable-count check would fire.
            time.sleep(8)

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            data = {"bins": []}
            for item in soup.select(".myaccount-block__item--bin"):
                title_el = item.select_one(".myaccount-block__title")
                if not title_el:
                    continue
                bin_type = title_el.get_text(strip=True)

                # The waste/recycling blocks wrap their date in a
                # "myaccount-block__date" <p>, but the Garden Waste block
                # just puts it in a plain <p> with no distinguishing
                # class, so search the whole item's text instead of a
                # specific date element.
                date_match = re.search(
                    r"[A-Za-z]{3} [A-Za-z]{3} \d{1,2} \d{4}", item.get_text()
                )
                if not date_match:
                    continue

                collection_date = datetime.strptime(date_match.group(), "%a %b %d %Y")
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )

            data["bins"].sort(
                key=lambda x: datetime.strptime(x["collectionDate"], date_format)
            )
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        return data
