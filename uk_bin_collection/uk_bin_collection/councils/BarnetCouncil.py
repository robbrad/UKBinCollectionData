from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
import json
import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def get_seasonal_overrides():
    url = "https://www.barnet.gov.uk/recycling-and-waste/bin-collections/find-your-bin-collection-day"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        body_div = soup.find("div", class_="field--name-body")
        ul_element = body_div.find("ul")
        if ul_element:
            li_elements = ul_element.find_all("li")
            overrides_dict = {}
            for li_element in li_elements:
                li_text = li_element.text.strip()
                li_text = re.sub(r"\([^)]*\)", "", li_text).strip()
                if "Collections for" in li_text and "will be revised to" in li_text:
                    parts = li_text.split("will be revised to")
                    original_date = (
                        parts[0]
                        .replace("Collections for", "")
                        .replace("\xa0", " ")
                        .strip()
                    )
                    revised_date = parts[1].strip()

                    # Extract day and month
                    date_parts = original_date.split()[1:]
                    if len(date_parts) == 2:
                        day, month = date_parts
                        # Ensure original_date has leading zeros for single-digit days
                        day = day.zfill(2)
                        original_date = f"{original_date.split()[0]} {day} {month}"

                    # Store the information in the dictionary
                    overrides_dict[original_date] = revised_date
            return overrides_dict
        else:
            print("UL element not found within the specified div.")
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")


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
            user_postcode = kwargs.get("postcode")
            if not user_postcode:
                raise ValueError("No postcode provided.")
            check_postcode(user_postcode)

            user_paon = kwargs.get("paon")
            check_paon(user_paon)
            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            driver = create_webdriver(web_driver, headless)
            page = "https://account.barnet.gov.uk/Forms/Home/Redirector/Index/?id=6a2ac067-3322-46e5-96e4-16c0c214454a&mod=OA&casetype=BAR&formname=BNTCOLDATE"
            driver.get(page)

            postcode_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[aria-label="Postcode"]')
                )
            )

            postcode_input.send_keys(user_postcode)

            find_address_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[value="Find address"]')
                )
            )
            find_address_button.click()

            time.sleep(5)
            # Wait for the element with aria-label="Postcode" to be present
            select_address_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[aria-label="Select your&nbsp;address"]')
                )
            )

            select = Select(select_address_input)
            select.select_by_visible_text(user_paon)

            # Wait for the specified div to be present
            target_div_id = "MainContent_CUSTOM_FIELD_808562d4b07f437ea751317cabd19d9ed93a174c32b14f839b65f6abc42d8108_div"
            target_div = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, target_div_id))
            )

            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Find the div with the specified id
            target_div = soup.find("div", {"id": target_div_id})

            overrides_dict = get_seasonal_overrides()

            # Check if the div is found
            if target_div:
                bin_data = {"bins": []}

                for bin_div in target_div.find_all(
                    "div",
                    {"style": re.compile("background-color:.*; padding-left: 4px;")},
                ):
                    bin_type = bin_div.find("strong").text.strip()
                    collection_date_string = (
                        re.search(r"Next collection date:\s+(.*)", bin_div.text)
                        .group(1)
                        .strip()
                        .replace(",", "")
                    )
                    if collection_date_string in overrides_dict:
                        # Replace with the revised date from overrides_dict
                        collection_date_string = overrides_dict[collection_date_string]

                    current_date = datetime.now()
                    parsed_date = datetime.strptime(
                        collection_date_string + f" {current_date.year}", "%A %d %B %Y"
                    )
                    # Check if the parsed date is in the past and not today
                    if parsed_date.date() < current_date.date():
                        # If so, set the year to the next year
                        parsed_date = parsed_date.replace(year=current_date.year + 1)
                    else:
                        # If not, set the year to the current year
                        parsed_date = parsed_date.replace(year=current_date.year)
                    formatted_date = parsed_date.strftime("%d/%m/%Y")

                    contains_date(formatted_date)
                    bin_info = {"type": bin_type, "collectionDate": formatted_date}
                    bin_data["bins"].append(bin_info)
            else:
                raise ValueError("Collection data not found.")

        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return bin_data
