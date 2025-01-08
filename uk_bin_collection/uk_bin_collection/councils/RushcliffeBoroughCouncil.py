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

            # Wait for the 'Select address' dropdown to appear and select option matching UPRN
            dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "FF3518-list"))
            )

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f"//select[@id='FF3518-list']/option[starts-with(@value, 'U{user_uprn}')]",
                    )
                )
            ).click()

            """# Create a 'Select' for it, then select the matching URPN option
            dropdownSelect = Select(dropdown)
            target_prefix = "U" + user_uprn
            for option in dropdownSelect.options:
                option_value = option.get_attribute("value")
                if option_value.startswith(target_prefix):  # Search by visible text
                    dropdownSelect.select_by_visible_text(option.text)
            # dropdownSelect.select_by_value("U" + user_uprn)"""

            # Wait for the submit button to appear, then click it to get the collection dates
            submit = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "submit-button"))
            )
            submit.click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ss_confPanel"))
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            bins_text = soup.find("div", id="body-content")

            if bins_text:
                results = re.findall(
                    "Your (.*?) bin will next be collected on (\d\d?\/\d\d?\/\d{4})",
                    bins_text.find("div", {"class": "ss_confPanel"}).get_text(),
                )
                if results:
                    for result in results:
                        collection_date = datetime.strptime(result[1], "%d/%m/%Y")
                        dict_data = {
                            "type": result[0],
                            "collectionDate": collection_date.strftime(date_format),
                        }
                        data["bins"].append(dict_data)

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
