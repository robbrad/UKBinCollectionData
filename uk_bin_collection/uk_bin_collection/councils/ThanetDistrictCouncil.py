import json
import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        url = f"https://www.thanet.gov.uk/wp-content/mu-plugins/collection-day/incl/mu-collection-day-calls.php?pAddress={user_uprn}"
        web_driver = kwargs.get("web_driver")
        headless = kwargs.get("headless")

        # Create the Selenium WebDriver
        driver = create_webdriver(web_driver, headless, None, __name__)

        try:
            print(f"Navigating to URL: {url}")
            driver.get(url)

            # Wait for Cloudflare to complete its check
            WebDriverWait(driver, 30).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            print("Page loaded successfully.")

            # Parse the page source with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Extract the JSON data from the page
            print("Extracting bin collection data...")
            body_content = soup.find("body").text
            if not body_content:
                raise ValueError("Expected JSON data not found in the <body> tag.")

            bin_collection = json.loads(body_content)

            # Process the bin collection data
            for collection in bin_collection:
                bin_type = collection["type"]
                collection_date = collection["nextDate"].split(" ")[0]

                dict_data = {
                    "type": bin_type,
                    "collectionDate": collection_date,
                }
                bindata["bins"].append(dict_data)

            # Sort the bins by collection date
            bindata["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
            )
            print(bindata)

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            print("Cleaning up WebDriver...")
            driver.quit()

        return bindata
