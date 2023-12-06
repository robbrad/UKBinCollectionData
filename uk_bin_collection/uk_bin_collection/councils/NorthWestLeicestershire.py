from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

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
        page = "https://nwleics-self.achieveservice.com/en/AchieveForms/?form_uri=sandbox-publish://AF-Process-bde93819-fa47-4bba-b094-bef375dbef0c/AF-Stage-b4ac5d55-7fb7-4c40-809f-4d1856399bed/definition.json&redirectlink=/en&cancelRedirectLink=/en&noLoginPrompt=1"

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
        inputElement_postcodesearch.send_keys(" ")

        # Wait for the 'Select your property' dropdown to appear and select the first result
        dropdown = wait.until(EC.element_to_be_clickable((By.NAME, "ChooseAddress")))

        dropdown_options = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "lookup-option"))
        )

        # Create a 'Select' for it, then select the first address in the list
        # (Index 0 is "Make a selection from the list")
        dropdownSelect = Select(dropdown)
        dropdownSelect.select_by_value(str(user_uprn))

        # Wait for the 'View more' link to appear, then click it to get the full set of dates
        next_btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "nextText")))

        next_btn.click()

        dropdown_options = wait.until(
            EC.presence_of_element_located((By.ID, "WasteCollections"))
        )

        soup = BeautifulSoup(driver.page_source, features="html.parser")

        wasteTable = soup.find("tbody", id="WasteCollections").find_all("tr")

        for row in wasteTable:
            rowdata = row.find_all("td")
            if len(rowdata) == 3:
                # Strip the day (i.e. Monday) out of the collection date string for parsing
                dateString = " ".join(rowdata[2].text.strip().split(" ")[1:])

                data["bins"].append(
                    {
                        "type": rowdata[1].text.strip(),
                        "collectionDate": datetime.strptime(
                            dateString, "%d %B %Y"
                        ).strftime(date_format),
                    }
                )

        return data
