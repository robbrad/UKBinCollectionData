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
        data = {"bins": []}
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        web_driver = kwargs.get("web_driver")
        headless = kwargs.get("headless")
        check_uprn(user_uprn)
        check_postcode(user_postcode)

        # Create Selenium webdriver
        driver = create_webdriver(web_driver, headless, None, __name__)
        driver.get("https://www.staffsmoorlands.gov.uk/findyourbinday")

        # Close cookies banner
        # cookieAccept = WebDriverWait(driver, 10).until(
        #    EC.presence_of_element_located(
        #        (By.CSS_SELECTOR, ".cookiemessage__link--close")
        #    )
        # )
        # cookieAccept.click()

        # Wait for the postcode field to appear then populate it
        inputElement_postcode = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.ID, "FINDBINDAYSSTAFFORDSHIREMOORLANDS_POSTCODESELECT_POSTCODE")
            )
        )
        inputElement_postcode.send_keys(user_postcode)

        # Click search button
        findAddress = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.ID,
                    "FINDBINDAYSSTAFFORDSHIREMOORLANDS_POSTCODESELECT_PAGE1NEXT_NEXT",
                )
            )
        )
        findAddress.click()

        # Wait for the 'Select address' dropdown to appear and select option matching UPRN
        dropdown = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.ID, "FINDBINDAYSSTAFFORDSHIREMOORLANDS_ADDRESSSELECT_ADDRESS")
            )
        )
        # Create a 'Select' for it, then select the matching URPN option
        dropdownSelect = Select(dropdown)
        dropdownSelect.select_by_value(user_uprn)

        # Wait for the submit button to appear, then click it to get the collection dates
        submit = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.ID,
                    "FINDBINDAYSSTAFFORDSHIREMOORLANDS_ADDRESSSELECT_ADDRESSSELECTNEXTBTN_NEXT",
                )
            )
        )
        submit.click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "bin-collection__month"))
        )

        soup = BeautifulSoup(driver.page_source, features="html.parser")

        # Quit Selenium webdriver to release session
        driver.quit()

        # Get months
        for month_wrapper in soup.find_all("div", {"class": "bin-collection__month"}):
            if month_wrapper:
                month_year = month_wrapper.find(
                    "h3", {"class": "bin-collection__title"}
                ).get_text(strip=True)
                # Get collections
                for collection in month_wrapper.find_all(
                    "li", {"class": "bin-collection__item"}
                ):
                    day = collection.find(
                        "span", {"class": "bin-collection__number"}
                    ).get_text(strip=True)
                    if month_year and day:
                        bin_date = datetime.strptime(day + " " + month_year, "%d %B %Y")
                        dict_data = {
                            "type": collection.find(
                                "span", {"class": "bin-collection__type"}
                            ).get_text(strip=True),
                            "collectionDate": bin_date.strftime(date_format),
                        }
                        data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return data
