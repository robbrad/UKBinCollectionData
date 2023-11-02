from bs4 import BeautifulSoup
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
        page = "https://selfservice.rushcliffe.gov.uk/renderform.aspx?t=1242&k=86BDCD8DE8D868B9E23D10842A7A4FE0F1023CCA"

        data = {"bins": []}

        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        web_driver = kwargs.get("web_driver")
        check_uprn(user_uprn)
        check_postcode(user_postcode)

        # Create Selenium webdriver
        driver = create_webdriver(web_driver)
        driver.get(page)

        # Populate postcode field
        inputElement_postcode = driver.find_element(
            By.ID,
            "ctl00_ContentPlaceHolder1_FF3518TB",
        )
        inputElement_postcode.send_keys(user_postcode)

        # Click search button
        driver.find_element(
            By.ID,
            "ctl00_ContentPlaceHolder1_FF3518BTN",
        ).click()

        # Wait for the 'Select address' dropdown to appear and select option matching UPRN
        dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_FF3518DDL"))
        )
        # Create a 'Select' for it, then select the matching URPN option
        dropdownSelect = Select(dropdown)
        dropdownSelect.select_by_value("U" + user_uprn)

        # Wait for the submit button to appear, then click it to get the collection dates
        submit = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_btnSubmit"))
        )
        submit.click()

        soup = BeautifulSoup(driver.page_source, features="html.parser")

        bins_text = soup.find("div", id="ctl00_ContentPlaceHolder1_pnlConfirmation")

        if bins_text:
            results = re.findall("Your (.*?) bin will next be collected on (\d\d?\/\d\d?\/\d{4})",
                                 bins_text.find("div", {"class": "ss_confPanel"}).get_text())
            if results:
                for result in results:
                    collection_date = datetime.strptime(result[1], "%d/%m/%Y")
                    dict_data = {
                        "type": result[0],
                        "collectionDate": collection_date.strftime(date_format),
                    }
                    data["bins"].append(dict_data)

                    data["bins"].sort(
                        key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
                    )

        return data
