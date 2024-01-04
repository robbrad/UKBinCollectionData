from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        if not user_postcode:
            raise ValueError("No postcode provided.")
        check_postcode(user_postcode)

        user_paon = kwargs.get("paon")
        check_paon(user_paon)

        web_driver = kwargs.get("web_driver")
        driver = create_webdriver(web_driver)
        page = "https://account.barnet.gov.uk/Forms/Home/Redirector/Index/?id=6a2ac067-3322-46e5-96e4-16c0c214454a&mod=OA&casetype=BAR&formname=BNTCOLDATE"
        driver.get(page)

        postcode_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Postcode"]'))
        )

        postcode_input.send_keys(user_postcode)

        find_address_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[value="Find address"]'))
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
        driver.quit()

        # Find the div with the specified id
        target_div = soup.find("div", {"id": target_div_id})

        # Check if the div is found
        if target_div:
            bin_data = {"bins": []}

            for bin_div in target_div.find_all(
                "div", {"style": re.compile("background-color:.*; padding-left: 4px;")}
            ):
                bin_type = bin_div.find("strong").text.strip()
                collection_date_string = (
                    re.search(r"Next collection date:\s+(.*)", bin_div.text)
                    .group(1)
                    .strip()
                )
                current_date = datetime.now()
                parsed_date = datetime.strptime(
                    collection_date_string + f" {current_date.year}", "%A, %d %B %Y"
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

        return bin_data
