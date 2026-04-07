import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            user_uprn = kwargs.get("uprn")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_uprn(user_uprn)
            # Pad UPRN with 0's at the start for any that aren't 12 chars
            user_uprn = user_uprn.zfill(12)

            # Create Selenium webdriver
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get(
                f"https://my.reigate-banstead.gov.uk/en/service/Bins_and_recycling___collections_calendar?uprn={user_uprn}"
            )

            # Wait for iframe to load and switch to it
            WebDriverWait(driver, 30).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "fillform-frame-1"))
            )

            # Wait for collection data to load (h3 elements contain dates)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "h3"))
            )

            time.sleep(3)

            # Make a BS4 object
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            data = {"bins": []}

            # Find all html2 spans - use the one with actual content (h3 elements)
            # There are multiple spans with data-name="html2"; the first is empty
            sections = soup.find_all("span", {"data-name": "html2"})
            section = None
            for s in sections:
                if s.find("h3"):
                    section = s
                    break

            if section:
                # Structure: each date group is a top-level div containing:
                #   - a div with an h3 (the date)
                #   - a div with a ul containing li elements (collection types in span tags)
                h3_elements = section.find_all("h3")
                for h3 in h3_elements:
                    date_text = h3.get_text(strip=True)
                    if not date_text:
                        continue

                    try:
                        collection_date = datetime.strptime(
                            date_text, "%A %d %B %Y"
                        ).strftime(date_format)
                    except ValueError:
                        continue

                    # Navigate up to the date's div, then to the sibling div with the ul
                    date_div = h3.find_parent("div")
                    if date_div:
                        # The next sibling div contains the collection types
                        collections_div = date_div.find_next_sibling("div")
                        if collections_div:
                            for li in collections_div.find_all("li"):
                                # Collection type is in a span inside each li
                                span = li.find("span")
                                if span:
                                    collection_type = span.get_text(strip=True)
                                else:
                                    collection_type = li.get_text(strip=True)
                                if collection_type:
                                    dict_data = {
                                        "type": collection_type,
                                        "collectionDate": collection_date,
                                    }
                                    data["bins"].append(dict_data)

            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
            )
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        return data
