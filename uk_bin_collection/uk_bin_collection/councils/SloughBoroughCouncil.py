import time
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

def get_street_from_postcode(postcode: str, api_key: str) -> str:
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": postcode, "key": api_key}
    response = requests.get(url, params=params)
    data = response.json()

    if data["status"] != "OK":
        raise ValueError(f"API error: {data['status']}")

    for component in data["results"][0]["address_components"]:
        if "route" in component["types"]:
            return component["long_name"]

    raise ValueError("No street (route) found in the response.")

class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        bin_data = {"bins": []}
        try:
            user_postcode = kwargs.get("postcode")
            if not user_postcode:
                raise ValueError("No postcode provided.")
            check_postcode(user_postcode)

            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            driver = create_webdriver(web_driver, headless, None, __name__)
            page = "https://www.slough.gov.uk/bin-collections"
            driver.get(page)

            # Accept cookies
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "ccc-recommended-settings"))
            ).click()

            # Enter the street name into the address search
            address_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "keyword_directory25"))
            )
            user_address = get_street_from_postcode(user_postcode, "AIzaSyBDLULT7EIlNtHerswPtfmL15Tt3Oc0bV8")
            address_input.send_keys(user_address + Keys.ENTER)

            # Wait for address results to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span.list__link-text"))
            )
            span_elements = driver.find_elements(By.CSS_SELECTOR, "span.list__link-text")

            for span in span_elements:
                if user_address.lower() in span.text.lower():
                    span.click()
                    break
            else:
                raise Exception(f"No link found containing address: {user_address}")

            # Wait for address detail page
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "section.site-content"))
            )
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Extract each bin link and type
            for heading in soup.select("dt.definition__heading"):
                heading_text = heading.get_text(strip=True)
                if "bin day details" in heading_text.lower():
                    bin_type = heading_text.split()[0].capitalize() + " bin"
                    dd = heading.find_next_sibling("dd")
                    link = dd.find("a", href=True)

                    if link:
                        bin_url = link["href"]
                        if not bin_url.startswith("http"):
                            bin_url = "https://www.slough.gov.uk" + bin_url

                        # Visit the child page
                        print(f"Navigating to {bin_url}")
                        driver.get(bin_url)
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.page-content"))
                        )
                        child_soup = BeautifulSoup(driver.page_source, "html.parser")

                        editor_div = child_soup.find("div", class_="editor")
                        if not editor_div:
                            print("No editor div found on bin detail page.")
                            continue

                        ul = editor_div.find("ul")
                        if not ul:
                            print("No <ul> with dates found in editor div.")
                            continue

                    for li in ul.find_all("li"):
                        raw_text = li.get_text(strip=True).replace(".", "")

                        if "no collection" in raw_text.lower() or "no collections" in raw_text.lower():
                            print(f"Ignoring non-collection note: {raw_text}")
                            continue

                        raw_date = raw_text

                        try:
                            parsed_date = datetime.strptime(raw_date, "%d %B %Y")
                        except ValueError:
                            raw_date_cleaned = raw_date.split("(")[0].strip()
                            try:
                                parsed_date = datetime.strptime(raw_date_cleaned, "%d %B %Y")
                            except Exception:
                                print(f"Could not parse date: {raw_text}")
                                continue

                        formatted_date = parsed_date.strftime("%d/%m/%Y")
                        contains_date(formatted_date)
                        bin_data["bins"].append({
                            "type": bin_type,
                            "collectionDate": formatted_date
                        })

                        print(f"Type: {bin_type}, Date: {formatted_date}") 

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        return bin_data