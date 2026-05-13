import json
import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium import webdriver
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
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        bindata = {"bins": []}
        driver = None
        web_driver = kwargs.get("web_driver")

        base_url = "https://westdevon.fccenvironment.co.uk"

        try:
            driver = create_webdriver(web_driver)
            driver.get(base_url)

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='text']")
                )
            )

            fcc_token = None
            for cookie in driver.get_cookies():
                if cookie["name"] == "fcc_session_cookie":
                    fcc_token = cookie["value"]
                    break

            if not fcc_token:
                raise ValueError(
                    "Could not obtain session token. Service may be unavailable."
                )

            if not user_uprn and user_postcode and user_paon:
                addr_js = f"""
                return await fetch('/ajaxprocessor/getaddresses', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-Requested-With': 'XMLHttpRequest'
                    }},
                    body: 'fcc_session_token={fcc_token}&postcode={user_postcode.replace(" ", "+")}'
                }}).then(r => r.json());
                """
                result = driver.execute_script(addr_js)
                addresses = result.get("addresses", {})

                if not addresses:
                    raise ValueError(
                        f"No addresses found for postcode {user_postcode}"
                    )

                paon_lower = user_paon.lower().strip()
                matched_uprn = None

                for entry in addresses.values():
                    addr_text = entry[1].lower().strip()
                    if addr_text.startswith(paon_lower + " "):
                        matched_uprn = entry[0]
                        break

                if not matched_uprn:
                    for entry in addresses.values():
                        addr_text = entry[1].lower().strip()
                        if paon_lower in addr_text:
                            matched_uprn = entry[0]
                            break

                if not matched_uprn:
                    first_entry = list(addresses.values())[0]
                    matched_uprn = first_entry[0]

                user_uprn = matched_uprn

            if not user_uprn:
                raise ValueError(
                    "Either uprn or postcode + house_number must be provided"
                )

            coll_js = f"""
            return await fetch('/ajaxprocessor/getcollectiondetails', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                }},
                body: 'fcc_session_token={fcc_token}&uprn={user_uprn}'
            }}).then(r => r.json());
            """
            result = driver.execute_script(coll_js)

            if result.get("error", {}).get("CodeName") == "CommProperty":
                raise ValueError(
                    "The provided address does not have a domestic waste service"
                )

            seen = set()

            for collection in result["binCollections"]["tile"]:
                soup = BeautifulSoup(collection[0], "html.parser")
                collections = soup.find_all("div", class_="collectionDiv")

                for coll in collections:
                    service_name = coll.find("h3").text.strip()

                    det_wrap = coll.find(
                        "div", class_="wdshDetWrap"
                    ) or coll.find("div", class_="detWrap")
                    if not det_wrap:
                        continue

                    details = det_wrap.text.strip()

                    if "Your next scheduled collection is" not in details:
                        continue

                    next_collection = details.split(
                        "Your next scheduled collection is "
                    )[1].split(".")[0]

                    if next_collection.startswith("today"):
                        next_collection = next_collection.split("today, ")[1]
                    elif next_collection.startswith("tomorrow"):
                        next_collection = next_collection.split(
                            "tomorrow, "
                        )[1]

                    collection_date = datetime.strptime(
                        next_collection, "%A, %d %B %Y"
                    ).strftime(date_format)

                    key = (service_name, collection_date)
                    if key in seen:
                        continue
                    seen.add(key)

                    dict_data = {
                        "type": service_name,
                        "collectionDate": collection_date,
                    }
                    bindata["bins"].append(dict_data)

            bindata["bins"].sort(
                key=lambda x: datetime.strptime(
                    x.get("collectionDate"), "%d/%m/%Y"
                )
            )

        finally:
            if driver:
                driver.quit()

        return bindata
