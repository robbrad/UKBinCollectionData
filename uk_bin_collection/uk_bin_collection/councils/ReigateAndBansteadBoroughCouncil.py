import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Set up Selenium to run 'headless'
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        # Pad UPRN with 0's at the start for any that aren't 12 chars
        user_uprn = user_uprn.zfill(12)

        # Create Selenium webdriver
        driver = webdriver.Chrome(options=options)
        driver.get(f"https://my.reigate-banstead.gov.uk/en/service/Bins_and_recycling___collections_calendar?uprn={user_uprn}")

        # Wait for iframe to load and switch to it
        WebDriverWait(driver, 30).until(EC.frame_to_be_available_and_switch_to_it((By.ID, 'fillform-frame-1')))

        # Wait for form
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span[data-name="html2"] > div')))

        # Make a BS4 object
        soup = BeautifulSoup(driver.page_source, features="html.parser")
        soup.prettify()

        data = {"bins": []}
        section = soup.find("span", {"data-name": "html2"})
        dates = section.find_all("div")
        for d in dates:
            date = d.find("h3")
            collections = d.find_all("li")
            if date and collections:
                collection_date = datetime.strptime(date.get_text(strip=True), "%A %d %B %Y").strftime(date_format)
                for c in collections:
                    collection_type = c.get_text(strip=True)
                    if c.get_text(strip=True):
                        dict_data = {
                            "type": collection_type,
                            "collectionDate": collection_date,
                        }
                        data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
