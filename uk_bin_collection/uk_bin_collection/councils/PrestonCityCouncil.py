from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

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
        web_driver = kwargs.get("web_driver")
        check_paon(user_paon)
        check_postcode(user_postcode)

        # Create Selenium webdriver
        driver = create_webdriver(web_driver)
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
        dropdown = WebDriverWait(driver, 10).until(
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

            data["bins"].append(
                {
                    "type": typeAndDateDivs[3].text,
                    "collectionDate": datetime.strptime(dateString, "%d/%m/%Y").strftime(date_format)
                }
            )

        return data
