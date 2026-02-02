from datetime import datetime
from time import sleep

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            page = (
                "https://myselfservice.ne-derbyshire.gov.uk/service/Check_your_Bin_Day"
            )

            data = {"bins": []}

            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_uprn(user_uprn)
            check_postcode(user_postcode)

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
            inputElement_postcodesearch.send_keys(str(user_postcode))

            dropdown = wait.until(EC.element_to_be_clickable((By.NAME, "selAddress")))
            dropdown_options = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "lookup-option"))
            )

            drop_down_values = Select(dropdown)
            option_element = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, f'option.lookup-option[value="{str(user_uprn)}"]')
                )
            )
            drop_down_values.select_by_value(str(user_uprn))

            h3_element = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//th[contains(text(), 'Waste Collection')]")
                )
            )

            sleep(2)

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            print("Parsing HTML content...")

            collection_rows = soup.find_all("tr")

            # Bin type mapping for cleaner logic
            bin_type_keywords = ["Black", "Burgundy", "Green"]

            for row in collection_rows:
                cells = row.find_all("td")
                if len(cells) == 3:  # Date, Image, Bin Type
                    # Extract date carefully
                    date_labels = cells[0].find_all("label")
                    collection_date = None
                    for label in date_labels:
                        label_text = label.get_text().strip()
                        if contains_date(label_text):
                            collection_date = label_text
                            break

                    # Extract bin type
                    bin_label = cells[2].find("label")
                    bin_types = bin_label.get_text().strip() if bin_label else None

                    if collection_date and bin_types:
                        print(f"Found collection: {collection_date} - {bin_types}")

                        # Parse date once
                        formatted_date = datetime.strptime(
                            collection_date, "%d/%m/%Y"
                        ).strftime(date_format)

                        # Check for each bin type keyword in the text
                        for bin_keyword in bin_type_keywords:
                            if bin_keyword in bin_types:
                                data["bins"].append(
                                    {
                                        "type": f"{bin_keyword} Bin",
                                        "collectionDate": formatted_date,
                                    }
                                )

            print(f"Found {len(data['bins'])} collections")
            print(f"Final data: {data}")

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        return data
