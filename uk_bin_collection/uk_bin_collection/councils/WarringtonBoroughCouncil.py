import json
import os
from datetime import datetime

import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        uri = f"https://www.warrington.gov.uk/bin-collections/get-jobs/{user_uprn}"

        if PLAYWRIGHT_AVAILABLE:
            bin_collection = self._fetch_playwright(uri)
        else:
            response = requests.get(uri, timeout=30)
            bin_collection = response.json()

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

    @staticmethod
    def _fetch_playwright(uri):
        import time
        from bs4 import BeautifulSoup

        proxy_url = os.environ.get("UKBCD_PLAYWRIGHT_PROXY")
        launch_args = {
            "headless": False,
            "args": ["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        }
        if proxy_url:
            launch_args["proxy"] = {"server": proxy_url}

        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_args)
            ctx = browser.new_context()
            page = ctx.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator, webdriver, {get: () => undefined})"
            )
            page.goto(uri, timeout=30000)
            time.sleep(8)
            content = page.content()
            ctx.close()
            browser.close()

        soup = BeautifulSoup(content, "html.parser")
        pre = soup.find("pre")
        if pre:
            return json.loads(pre.text)
        raise ValueError("No JSON data found on page")
