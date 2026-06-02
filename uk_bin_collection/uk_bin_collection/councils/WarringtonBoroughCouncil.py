import json
import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        uri = f"https://www.warrington.gov.uk/bin-collections/get-jobs/{user_uprn}"

        web_driver = kwargs.get("web_driver")
        headless = kwargs.get("headless")

        driver = create_webdriver(web_driver, headless, None, __name__)
        try:
            driver.get(uri)
            # Wait for Cloudflare challenge to resolve and JSON to appear
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )
            time.sleep(2)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            pre = soup.find("pre")
            if not pre:
                raise ValueError("No JSON data found on page after Cloudflare challenge")

            bin_collection = json.loads(pre.text)
        finally:
            driver.quit()

        for collection in bin_collection.get("schedule", []):
            bin_type = collection["Name"]
            collection_date = collection["ScheduledStart"]
            bindata["bins"].append({
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    collection_date, "%Y-%m-%dT%H:%M:%S"
                ).strftime(date_format),
            })

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )
        return bindata
