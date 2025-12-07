import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        """
        Parse bin collection data for a given postcode and house identifier by driving the council bin-calendar web UI and returning structured collection entries.
        
        Parameters:
            page (str): Unused; kept for API compatibility.
            postcode (str, in kwargs): The postcode to search for.
            paon (str, in kwargs): The property identifier (house number or name) used to pick the best address option from the dropdown.
            web_driver (str, optional, in kwargs): WebDriver backend identifier passed to the webdriver factory.
            headless (bool, optional, in kwargs): Whether to run the browser in headless mode.
        
        Returns:
            dict: A dictionary with a "bins" key containing a list of entries. Each entry is a dict with:
                - "type": the collection colour/name extracted from the image alt text (or None if missing).
                - "collectionDate": the collection date string formatted according to the module's date_format.
        
        Raises:
            ValueError: If the provided paon cannot be matched to any dropdown address or if the collections table cannot be found.
        """
        driver = None
        try:
            # Get and check UPRN
            user_postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")
            check_postcode(user_postcode)
            check_paon(user_paon)

            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            bindata = {"bins": []}

            URL = "https://fife.portal.uk.empro.verintcloudservices.com/site/fife/request/bin_calendar"

            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get(URL)

            wait = WebDriverWait(driver, 30)

            ID_POSTCODE = "dform_widget_ps_45M3LET8_txt_postcode"
            ID_SEARCH_BTN = "dform_widget_ps_3SHSN93_searchbutton"
            ID_ADDRESS_SELECT = "dform_widget_ps_3SHSN93_id"
            ID_COLLECTIONS = "dform_table_tab_collections"

            # Wait for initial page load and Cloudflare bypass
            wait.until(lambda d: "Just a moment" not in d.title and d.title != "")
            time.sleep(3)

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = wait.until(
                EC.presence_of_element_located((By.ID, ID_POSTCODE))
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = wait.until(EC.element_to_be_clickable((By.ID, ID_SEARCH_BTN)))
            findAddress.click()

            # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
            select_el = wait.until(
                EC.visibility_of_element_located((By.ID, ID_ADDRESS_SELECT))
            )
            wait.until(lambda d: len(Select(select_el).options) > 1)

            paon_norm = str(user_paon).strip().casefold()
            sel = Select(select_el)

            time.sleep(10)

            def _best_option():
                # Prefer exact contains on visible text; fallback to casefold contains
                """
                Selects the first dropdown option whose visible text contains the normalized PAON.
                
                Performs a case-insensitive containment check using the precomputed `paon_norm` against each option's visible text and returns the first match.
                
                Returns:
                    `WebElement` of the first matching option if found, `None` otherwise.
                """
                for opt in sel.options:
                    txt = (opt.text or "").strip()
                    if paon_norm and paon_norm in txt.casefold():
                        return opt
                return None

            opt = _best_option()
            if not opt:
                raise ValueError(
                    f"Could not find an address containing '{user_paon}' in the dropdown."
                )
            sel.select_by_visible_text(opt.text)

            # After selecting, the collections table should (re)render; wait for it
            wait.until(EC.presence_of_element_located((By.ID, ID_COLLECTIONS)))
            # Also wait until at least one data row is present (beyond headers)
            wait.until(
                lambda d: len(
                    d.find_elements(By.CSS_SELECTOR, f"#{ID_COLLECTIONS} .dform_tr")
                )
                > 1
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            table = soup.find("div", id=ID_COLLECTIONS)
            if not table:
                raise ValueError(
                    f"Could not find collections table by id='{ID_COLLECTIONS}'"
                )

            rows = table.find_all("div", class_="dform_tr")

            # Skip header row (first row with .dform_th entries)
            for row in rows[1:]:
                tds = row.find_all("div", class_="dform_td")
                if len(tds) < 3:
                    continue

                # Colour comes from the <img alt="...">
                colour_cell = tds[0]
                img = colour_cell.find("img")
                colour = img.get("alt").strip() if img and img.has_attr("alt") else None

                # Date text
                raw_date = tds[1].get_text(strip=True)
                # Example: "Wednesday, November 12, 2025"
                dt = datetime.strptime(raw_date, "%A, %B %d, %Y")

                dict_data = {
                    "type": colour,
                    "collectionDate": dt.strftime(date_format),
                }
                bindata["bins"].append(dict_data)

            bindata["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
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
        return bindata