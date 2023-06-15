from datetime import datetime

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass

# import the wonderful Beautiful Soup and the URL grabber


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        page = "https://selfservice.preston.gov.uk/service/Forms/FindMyNearest.aspx?Service=bins"

        data = {"bins": []}

        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        check_paon(user_paon)
        check_postcode(user_postcode)

        # Set up Selenium to run 'headless'
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # Create Selenium webdriver
        driver = webdriver.Chrome(options=options)
        driver.get(page)

        # If you bang in the house number (or property name) and postcode in the box it should find your property
        inputElement_address = driver.find_element(
            By.ID,
            "MainContent_txtAddress",
        )

        inputElement_address.send_keys(user_paon)
        inputElement_address.send_keys(" ")
        inputElement_address.send_keys(user_postcode)

        driver.find_element(
            By.ID,
            "btnSearch",
        ).click()

        # Wait for the 'Select your property' dropdown to appear and select the first result
        dropdown = WebDriverWait(driver,10).until(
            EC.presence_of_element_located((By.ID, "MainContent_ddlSearchResults"))
        )
        # Create a 'Select' for it, then select the first address in the list
        # (Index 0 is "Make a selection from the list")
        dropdownSelect = Select(dropdown)
        dropdownSelect.select_by_index(1)

        # Wait for the 'View more' link to appear, then click it to get the full set of dates
        viewMoreLink = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.LINK_TEXT, "View more collection dates"))
        )
        viewMoreLink.click()

        soup = BeautifulSoup(driver.page_source, features="html.parser")

        topLevelSpan = soup.find(
            "span",
            id="lblCollectionDates"
        )
        
        collectionDivs = topLevelSpan.findChildren(recursive=False)
        for collectionDiv in collectionDivs:
            # Each date has two child divs - the date and the bin type
            # However both strings are in <b> tags so there are 4 children, the text is at:
            # Index 1 - date string i.e. 'Monday 01/01/2023'
            # Index 3 - bin type i.e. 'General waste'
            typeAndDateDivs = collectionDiv.findChildren()
            
            # Strip the day (i.e. Monday) out of the collection date string for parsing
            dateString = typeAndDateDivs[1].text.split(' ')[1]

            # Bins are expected to be left out at 7AM, add that to date object for output
            sevenAm = datetime.strptime("070000", "%H%M%S").time()
            date_obj = datetime.strptime(dateString, "%d/%m/%Y")
            combined_date = datetime.combine(date_obj, sevenAm).strftime(
                "%d/%m/%Y %H:%M:%S"
            )

            data["bins"].append(
                {
                    "type": typeAndDateDivs[3].text,
                    "collectionDate": combined_date
                }
            )

        return data
