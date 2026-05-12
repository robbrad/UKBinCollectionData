import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

AJAX_URL = "https://www.durham.gov.uk/apiserver/ajaxlibrary/"


def _resolve_uprn_from_postcode(postcode, paon=None):
    """Use Durham's JSON-RPC PostcodeLookup to find UPRN from postcode + house number."""
    payload = {
        "jsonrpc": "2.0",
        "method": "durham.Localities.PostcodeLookup",
        "params": {"postcode": postcode},
        "id": "1",
        "name": "V2 AJAX End Point Library Worker",
    }
    resp = requests.post(AJAX_URL, json=payload, timeout=30)
    resp.raise_for_status()
    result_xml = resp.json().get("result", "")

    uprns = re.findall(r"<uprn[^>]*>([^<]+)</uprn>", result_xml)
    addrs = re.findall(r"<formatted_address[^>]*>([^<]+)</formatted_address>", result_xml)
    if not uprns:
        raise ValueError(f"No addresses found for postcode: {postcode}")

    entries = []
    for u, a in zip(uprns, addrs):
        entries.append({"address": a, "uprn": u})

    if paon:
        paon_norm = str(paon).strip().upper()
        for entry in entries:
            addr = entry["address"].upper()
            if addr.startswith(paon_norm + " ") or addr.startswith(paon_norm + ","):
                return entry["uprn"]
        for entry in entries:
            addr = entry["address"].upper()
            if paon_norm in addr:
                return entry["uprn"]

    return entries[0]["uprn"]


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        headless = kwargs.get("headless")
        web_driver = kwargs.get("web_driver")

        if not user_uprn and user_postcode:
            user_uprn = _resolve_uprn_from_postcode(user_postcode, user_paon)

        if not user_uprn:
            raise ValueError("Could not resolve address. Provide a postcode or UPRN.")

        url = f"https://www.durham.gov.uk/bincollections?uprn={user_uprn}"

        driver = create_webdriver(web_driver, headless, None, __name__)
        try:
            driver.get(url)

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".binsrubbish, .binsrecycling")
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")
        finally:
            driver.quit()

        data = {"bins": []}

        for bin_type in ["rubbish", "recycling", "gardenwaste"]:
            bin_info = soup.find(class_=f"bins{bin_type}")

            if bin_info:
                collection_text = bin_info.get_text(strip=True)

                if collection_text:
                    results = re.search(r"\d\d? [A-Za-z]+ \d{4}", collection_text)
                    if results:
                        date = datetime.strptime(results[0], "%d %B %Y")
                        data["bins"].append(
                            {
                                "type": bin_type,
                                "collectionDate": date.strftime(date_format),
                            }
                        )

        return data
