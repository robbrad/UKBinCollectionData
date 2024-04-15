from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait



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
            data = {"bins": []}
            collections = []

            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            driver = create_webdriver(web_driver, headless)
            # driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
            driver.get(
                "https://webapps.sunderland.gov.uk/WEBAPPS/WSS/Sunderland_Portal/Forms/bindaychecker.aspx"
            )

            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.ID, "ContentPlaceHolder1_tbPostCode_controltext")
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            inputElement_submit_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable(
                    (By.ID, "ContentPlaceHolder1_btnLLPG")
                )
            )
            inputElement_submit_button.click()

            addressList = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.ID, "ContentPlaceHolder1_ddlAddresses")
                )
            )
            selected_addressList = Select(addressList)
            for idx, addr_option in enumerate(selected_addressList.options):
                option_name = addr_option.accessible_name[0:len(user_paon)]
                if option_name == user_paon:
                    break
            selected_addressList.select_by_index(idx)

            # Make a BS4 object
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            household_bin_date = datetime.strptime(soup.find("span", {"id": "ContentPlaceHolder1_LabelHouse"}).get_text(strip=True), "%A %d %B %Y")
            collections.append(("Household bin", household_bin_date))

            recycling_bin_date = datetime.strptime(soup.find("span", {"id": "ContentPlaceHolder1_LabelRecycle"}).get_text(strip=True), "%A %d %B %Y")
            collections.append(("Recycling bin", recycling_bin_date))

            ordered_data = sorted(collections, key=lambda x: x[1])
            for item in ordered_data:
                dict_data = {
                    "type": item[0].capitalize(),
                    "collectionDate": item[1].strftime(date_format),
                }
                data["bins"].append(dict_data)

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
