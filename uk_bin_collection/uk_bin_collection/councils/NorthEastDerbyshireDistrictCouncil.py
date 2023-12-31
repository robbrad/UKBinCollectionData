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
        page = "https://myselfservice.ne-derbyshire.gov.uk/service/Check_your_Bin_Day"

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

        inputElement_postcodesearch.send_keys(str(user_postcode))

        # Wait for the 'Select your property' dropdown to appear and select the first result
        dropdown = wait.until(EC.element_to_be_clickable((By.NAME, "selAddress")))

        dropdown_options = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "lookup-option"))
        )

        # Create a 'Select' for it, then select the first address in the list
        # (Index 0 is "Make a selection from the list")
        drop_down_values = Select(dropdown)
        option_element = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, f'option.lookup-option[value="{str(user_uprn)}"]')
            )
        )

        drop_down_values.select_by_value(str(user_uprn))

        # Wait for the 'View more' link to appear, then click it to get the full set of dates
        h3_element = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//th[contains(text(), 'Waste Collection')]")
            )
        )

        soup = BeautifulSoup(driver.page_source, features="html.parser")

        target_h3 = soup.find("h3", string="Collection Details")
        tables_after_h3 = target_h3.parent.parent.find_next("table")

        table_rows = tables_after_h3.find_all("tr")
        for row in table_rows:
            rowdata = row.find_all("td")
            if len(rowdata) == 3:
                labels = rowdata[0].find_all("label")
                # Strip the day (i.e., Monday) out of the collection date string for parsing
                if len(labels) >= 2:
                    date_label = labels[1]
                    datestring = date_label.text.strip()

                # Add the bin type and collection date to the 'data' dictionary
                data["bins"].append(
                    {
                        "type": rowdata[2].text.strip(),
                        "collectionDate": datetime.strptime(
                            datestring, "%d/%m/%Y"
                        ).strftime(
                            date_format
                        ),  # Format the date as needed
                    }
                )

        return data
