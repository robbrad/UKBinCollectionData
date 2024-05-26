import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys

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
            page = "https://portal.walthamforest.gov.uk/AchieveForms/?mode=fill&consentMessage=yes&form_uri=sandbox-publish://AF-Process-d62ccdd2-3de9-48eb-a229-8e20cbdd6393/AF-Stage-8bf39bf9-5391-4c24-857f-0dc2025c67f4/definition.json&process=1&process_uri=sandbox-processes://AF-Process-d62ccdd2-3de9-48eb-a229-8e20cbdd6393&process_id=AF-Process-d62ccdd2-3de9-48eb-a229-8e20cbdd6393"

            data = {"bins": []}

            user_postcode = kwargs.get("postcode")
            user_uprn = kwargs.get("uprn")
            user_paon = kwargs.get("paon")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            iframe_presense = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "fillform-frame-1"))
            )

            driver.switch_to.frame(iframe_presense)
            wait = WebDriverWait(driver, 60)
            inputElement_postcodesearch = wait.until(
                EC.element_to_be_clickable((By.NAME, "postcode_search"))
            )

            inputElement_postcodesearch.send_keys(user_postcode)
            find_address_button = wait.until(
                EC.element_to_be_clickable((By.ID, "lookupPostcode"))
            )

            find_address_button.send_keys(Keys.RETURN)

            dropdown = wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "select2-choice"))
            )

            time.sleep(1)
            dropdown.click()

            dropdown_search = wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "select2-input"))
            )
            dropdown_search.click()

            dropdown_search.send_keys(user_paon)
            dropdown_search.send_keys(Keys.RETURN)

            find_ac_button = wait.until(
                EC.element_to_be_clickable((By.ID, "confirmSearchUPRN"))
            )

            find_ac_button.send_keys(Keys.RETURN)
            h4_element = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h4[contains(text(), 'Your Collections')]")
                )
            )

            data_table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        '//div[contains(@class, "fieldContent")]',
                    )
                )
            )
            # Make a BS4 object
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            data = {"bins": []}

            collection_divs = soup.find_all("div", {"style": "text-align: center;"})

            for collection_div in collection_divs:
                h5_tag = collection_div.find("h5")
                p_tag = collection_div.find("p")

                if h5_tag and p_tag:
                    bin_type = h5_tag.get_text(strip=True)
                    collection_date_text = p_tag.find("b").get_text(strip=True)

                    # Extract and format the date
                    date_match = re.search(r"(\d+ \w+)", collection_date_text)
                    if date_match:
                        date_str = date_match.group(1)
                        date_obj = datetime.strptime(
                            date_str + " " + str(datetime.today().year), "%d %B %Y"
                        )
                        collection_date = get_next_occurrence_from_day_month(
                            date_obj
                        ).strftime(date_format)

                        data["bins"].append(
                            {"type": bin_type, "collectionDate": collection_date}
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
