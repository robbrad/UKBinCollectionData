from bs4 import BeautifulSoup
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
        driver = None
        try:
            page = "https://selfservice.rushcliffe.gov.uk/renderform.aspx?t=1242&k=86BDCD8DE8D868B9E23D10842A7A4FE0F1023CCA"

            data = {"bins": []}

            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_uprn(user_uprn)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            # Populate postcode field
            inputElement_postcode = driver.find_element(
                By.ID,
                "FF3518-text",
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            driver.find_element(
                By.ID,
                "FF3518-find",
            ).click()

            # Wait for the 'Select address' dropdown to be visible and select option matching UPRN
            dropdown = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "FF3518-list"))
            )

            # Create a 'Select' for it, then select the matching URPN option
            dropdownSelect = Select(dropdown)
            found_uprn = False
            for o in dropdownSelect.options:
                ov = o.get_dom_attribute("value")
                if "U" + user_uprn in ov:
                    dropdownSelect.select_by_value(ov)
                    found_uprn = True
                    break

            if not found_uprn:
                raise Exception("could not find UPRN " + user_uprn + " in list")

            # Click submit button
            driver.find_element(
                By.ID,
                "submit-button",
            ).click()

            # Wait for the confirmation panel to appear
            conf_div = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ss_confPanel"))
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            bins_text = soup.find("div", id="body-content")

            if bins_text:
                results = re.findall(
                    r"Your next (.*?)(?:\s\(.*\))? bin collections will be (\d\d?\/\d\d?\/\d{4}) and (\d\d?\/\d\d?\/\d{4})",
                    bins_text.get_text(),
                )
                if results:
                    for result in results:
                        collection_one = datetime.strptime(result[1], "%d/%m/%Y")
                        data["bins"].append(
                            {
                                "type": result[0],
                                "collectionDate": collection_one.strftime(date_format),
                            }
                        )
                        collection_two = datetime.strptime(result[2], "%d/%m/%Y")
                        data["bins"].append(
                            {
                                "type": result[0],
                                "collectionDate": collection_two.strftime(date_format),
                            }
                        )

                    data["bins"].sort(
                        key=lambda x: datetime.strptime(
                            x.get("collectionDate"), "%d/%m/%Y"
                        )
                    )
        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return data
