from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
import time
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
            data = {"bins": []}

            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            # Create Selenium webdriver
            page = (
                f"https://webapp.halton.gov.uk/PublicWebForms/WasteServiceSearchv1.aspx"
            )

            driver = create_webdriver(web_driver, headless)
            driver.get(page)

            # If you bang in the house number (or property name) and postcode in the box it should find your property

            # iframe_presense = WebDriverWait(driver, 30).until(
            #    EC.presence_of_element_located((By.ID, "fillform-frame-1"))
            # )

            # driver.switch_to.frame(iframe_presense)
            wait = WebDriverWait(driver, 60)

            inputElement_property = wait.until(
                EC.element_to_be_clickable(
                    (By.NAME, "ctl00$ContentPlaceHolder1$txtProperty")
                )
            )
            inputElement_property.send_keys(user_paon)

            inputElement_postcodesearch = wait.until(
                EC.element_to_be_clickable(
                    (By.NAME, "ctl00$ContentPlaceHolder1$txtPostcode")
                )
            )
            inputElement_postcodesearch.send_keys(user_postcode)
            time.sleep(1)
            wait.until(
                EC.frame_to_be_available_and_switch_to_it(
                    (
                        By.CSS_SELECTOR,
                        "iframe[name^='a-'][src^='https://www.google.com/recaptcha/api2/anchor?']",
                    )
                )
            )
            wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[@id='recaptcha-anchor']"))
            ).send_keys(Keys.ENTER)
            time.sleep(5)
            driver.switch_to.default_content()
            search_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="ContentPlaceHolder1_btnSearch"]')
                )
            )
            search_btn.send_keys(Keys.ENTER)
            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Find all tab panels within the collectionTabs
            # Find all anchor elements within the collectionTabs
            anchor_elements = soup.select("#collectionTabs a.ui-tabs-anchor")

            for anchor in anchor_elements:
                # Extract the type of waste from the anchor text
                waste_type = anchor.text.strip()

                # Find the corresponding panel using the href attribute
                panel_id = anchor.get("href")
                panel = soup.select_one(panel_id)

                # Find all ul elements within the corresponding panel
                ul_elements = panel.find_all("ul")

                # Check if there are at least two ul elements
                if len(ul_elements) >= 2:
                    # Get the second ul element and extract its li elements
                    second_ul = ul_elements[1]
                    li_elements = second_ul.find_all("li")

                    # Extract the text content of each li element
                    date_texts = [
                        re.sub(r"[^a-zA-Z0-9,\s]", "", li.get_text(strip=True)).strip()
                        for li in li_elements
                    ]

                    for date_text in date_texts:
                        # Extracting dates from the text using simple text manipulation
                        # Assuming the dates are in the format: "Friday 15th December 2023", "Friday 22nd December 2023", etc.
                        # Parse the date string into a datetime object
                        date_string_without_ordinal = re.sub(
                            r"(\d+)(st|nd|rd|th)", r"\1", date_text
                        )

                        parsed_date = datetime.strptime(
                            date_string_without_ordinal, "%A %d %B %Y"
                        )

                        # Format the datetime object into the desired format '%d/%m/%Y'
                        formatted_date = parsed_date.strftime("%d/%m/%Y")

                        # Add extracted data to the 'bins' list
                        data["bins"].append(
                            {
                                "type": waste_type.capitalize(),
                                "collectionDate": formatted_date,
                            }
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
