from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

import time
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
        page = "https://my.portsmouth.gov.uk/en/AchieveForms/?form_uri=sandbox-publish://AF-Process-26e27e70-f771-47b1-a34d-af276075cede/AF-Stage-cd7cc291-2e59-42cc-8c3f-1f93e132a2c9/definition.json&redirectlink=%2F&cancelRedirectLink=%2F"

        data = {"bins": []}

        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        web_driver = kwargs.get("web_driver")
        check_uprn(user_uprn)
        check_postcode(user_postcode)
        # Create Selenium webdriver
        driver = create_webdriver(web_driver)
        driver.get(page)

        # If you bang in the house number (or property name) and postcode in the box it should find your property

        iframe_presense = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "fillform-frame-1"))
        )

        driver.switch_to.frame(iframe_presense)
        wait = WebDriverWait(driver, 60)
        inputElement_postcodesearch = wait.until(
            EC.element_to_be_clickable((By.NAME, "postcode_search"))
        )

        inputElement_postcodesearch.send_keys(user_postcode)
        lookupAddress_btn = wait.until(
            EC.element_to_be_clickable((By.ID, "lookupAddress"))
        )

        lookupAddress_btn.click()

        # Wait for the 'Select your property' dropdown to appear and select the first result
        dropdown = wait.until(EC.element_to_be_clickable((By.NAME, "Choose_Address")))

        dropdown_options = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "lookup-option"))
        )
        time.sleep(1)
        # Create a 'Select' for it, then select the first address in the list
        # (Index 0 is "Make a selection from the list")
        dropdownSelect = Select(dropdown)
        dropdownSelect.select_by_value(str(user_uprn))

        h4_element = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//h4[contains(text(), 'next 10 collection dates')]")
            )
        )

        soup = BeautifulSoup(driver.page_source, features="html.parser")
        # Define your XPath
        elements_with_data_field_name = soup.find_all(
            lambda tag: tag.has_attr("data-field-name")
            and tag["data-field-name"].startswith("html")
        )
        if elements_with_data_field_name:
            for element in elements_with_data_field_name:
                # Extract h4 text from the current element
                h4_text = (
                    element.find("h4").get_text(strip=True)
                    if element.find("h4")
                    else None
                )

                # Process the data (dates) in the current element (p tags)

                if h4_text:
                    if "next 10" in h4_text:
                        data_paragraphs = element.find_all("p") if element else []

                        # Extract dates from the first <p> tag (assuming dates are in the first <p> tag)
                        dates_paragraph = (
                            data_paragraphs[0] if len(data_paragraphs) > 0 else None
                        )
                        dates = (
                            dates_paragraph.find_all(string=True, recursive=False)
                            if dates_paragraph
                            else []
                        )

                        for date in dates:
                            data["bins"].append(
                                {
                                    "type": h4_text.split(" - ")[0],
                                    "collectionDate": datetime.strptime(
                                        re.sub(r"[^a-zA-Z0-9,\s]", "", date).strip(),
                                        "%A %d %B %Y",
                                    ).strftime("%d/%m/%Y"),
                                }
                            )

        return data
