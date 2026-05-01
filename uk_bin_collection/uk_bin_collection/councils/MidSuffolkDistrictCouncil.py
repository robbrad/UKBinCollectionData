import datetime
import re
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# Matches the council's date format e.g. "Wed 27 May 2026". Used to extract
# every date in a <p> tag — a single tag can contain multiple dates separated
# by commas when the council renders "Following Collections:" with two
# upcoming dates, and may be prefixed "Today - <date>".
_DATE_RE = re.compile(
    r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) \d{1,2} "
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}\b"
)


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            user_postcode = kwargs.get("postcode")
            if not user_postcode:
                raise ValueError("No postcode provided.")
            check_postcode(user_postcode)
            user_paon = kwargs.get("paon")
            if not user_paon:
                raise ValueError("No house name/number provided.")
            check_paon(user_paon)

            data = {"bins": []}

            url = "https://www.midsuffolk.gov.uk/check-your-collection-day"

            # Get our initial session running
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(url)

            # Enter postcode
            postcode_input = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[aria-label="Postcode"]')
                )
            )
            postcode_input.send_keys(user_postcode)

            # Click find address
            find_address_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "lfr-btn-label"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", find_address_button)
            driver.execute_script("arguments[0].click();", find_address_button)

            # Wait for address dropdown to appear AND populate. Polling for a
            # populated <select> beats a fixed sleep — the dropdown typically
            # renders in <1s, so a 5s sleep just held Chrome idle and let the
            # parallel Grid+local Chromes overlap memory peaks. On a busy
            # Selenium Grid that overlap is what triggered the
            # `__clone` / OOM crash inside the Grid container. Now we exit as
            # soon as options are available.
            def _populated_select(d):
                selects = d.find_elements(By.CSS_SELECTOR, "select")
                for s in selects:
                    if len(s.find_elements(By.TAG_NAME, "option")) > 1:
                        return s
                return False

            select_address_input = WebDriverWait(driver, 30).until(_populated_select)

            # Select address based on postcode and house number. Iterate and
            # prefer an exact-prefix match over substring matches so e.g.
            # "ANNEXE 91 THE COMMON" doesn't beat "91 THE COMMON" when the
            # caller asked for house number 91.
            select = Select(select_address_input)
            postcode_upper = user_postcode.upper()
            paon_str = str(user_paon).upper()

            best_value = None
            best_priority = 99
            for addr_option in select.options:
                if not addr_option.text or addr_option.text.strip() == "":
                    continue
                option_text = addr_option.text.upper()
                if postcode_upper not in option_text:
                    continue

                if option_text.startswith(f"{paon_str} "):
                    priority = 0
                elif (
                    f", {paon_str}," in option_text
                    or f", {paon_str} " in option_text
                    or option_text.endswith(f", {paon_str}")
                ):
                    priority = 1
                elif f", {paon_str}A," in option_text:
                    priority = 2
                elif f" {paon_str} " in option_text:
                    # Fallback substring match (e.g. "ANNEXE 91 THE COMMON").
                    priority = 3
                else:
                    continue

                if priority < best_priority:
                    best_priority = priority
                    best_value = addr_option.get_attribute("value")
                    if priority == 0:
                        break

            if best_value is None:
                raise ValueError(
                    f"Address not found for postcode {user_postcode} and house number {user_paon}"
                )
            select.select_by_value(best_value)

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "collection-cards"))
            )
            # Wait until at least one card has populated — the JS observer
            # builds cards asynchronously after the select change, and reading
            # page_source the instant #collection-cards appears can return an
            # empty container. Bound on cards rather than a fixed sleep.
            WebDriverWait(driver, 30).until(
                lambda d: len(
                    d.find_elements(
                        By.CSS_SELECTOR, "#collection-cards .card h3"
                    )
                )
                > 0
            )

            # Parse the HTML content
            soup = BeautifulSoup(driver.page_source, "html.parser")

            collection_cards = soup.find("div", class_="collection-cards")
            if collection_cards:
                cards = collection_cards.find_all("div", class_="card")
                for card in cards:
                    collection_type = (card.find("h3")).get_text()
                    # print(collection_type)
                    p_tags = card.find_all("p")  # any <p>

                    for p_tag in p_tags:
                        text = p_tag.get_text()
                        if text.startswith("Frequency"):
                            continue

                        # A single <p> can contain multiple dates — the
                        # "Following Collections:" tag renders comma-separated
                        # dates when the council has 3 upcoming collections,
                        # and "Next Collection:" can be prefixed with
                        # "Today - <date>". Pull every well-formed date out
                        # of the text and emit one entry per date.
                        for date_str in _DATE_RE.findall(text):
                            collection_date = datetime.strptime(
                                date_str, "%a %d %b %Y"
                            )
                            data["bins"].append(
                                {
                                    "type": collection_type,
                                    "collectionDate": collection_date.strftime(
                                        date_format
                                    ),
                                }
                            )
        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return data
