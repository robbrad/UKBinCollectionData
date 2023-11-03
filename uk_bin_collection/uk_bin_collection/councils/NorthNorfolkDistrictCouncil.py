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
        page = "https://forms.north-norfolk.gov.uk/outreach/BinCollectionDays.ofml"

        data = {"bins": []}

        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        web_driver = kwargs.get("web_driver")
        check_paon(user_paon)
        check_postcode(user_postcode)

        # Create Selenium webdriver
        driver = create_webdriver(web_driver)
        driver.get(page)

        # Populate postcode field
        inputElement_postcode = driver.find_element(
            By.ID,
            "F_Address_subform:Postcode",
        )
        inputElement_postcode.send_keys(user_postcode)

        # Click search button
        driver.find_element(
            By.ID,
            "BA_Address_subform:Search_button",
        ).click()

        # Wait for the 'Select address' dropdown to appear
        dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//select[@id='F_Address_subform:Id']"))
        )
        # Create a 'Select' for it, then select the matching house number/name option
        dropdownSelect = Select(dropdown)
        matchingOptions = [o for o in dropdownSelect.options if user_paon.lower() in o.text.lower()]
        if matchingOptions:
            matchingOptions[0].click()

            # Wait for the results to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'fieldmergedcolumn')]/ul"))
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Quit Selenium webdriver to release session
            driver.quit()

            bins_text = soup.find("div", id="Search_result_details_cps_hd")

            if bins_text:
                results = re.findall("Your next (.*?) Bin collection is ([A-Za-z]+ \\d\\d? [A-Za-z]+)",
                                     bins_text.get_text())
                if results:
                    for result in results:
                        collection_date = datetime.strptime(result[1] + " " + datetime.now().strftime("%Y"),
                                                            "%A %d %B %Y")
                        dict_data = {
                            "type": result[0],
                            "collectionDate": collection_date.strftime(date_format),
                        }
                        data["bins"].append(dict_data)

                        data["bins"].sort(
                            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
                        )
        else:
            raise ValueError("No matching address for house number/name found.")

        return data
