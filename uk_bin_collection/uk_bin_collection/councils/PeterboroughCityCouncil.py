import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

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
            user_poan = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            if not user_postcode:
                raise ValueError("No postcode provided.")
            check_postcode(user_postcode)

            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            driver = create_webdriver(web_driver, headless, None, __name__)
            page = "https://report.peterborough.gov.uk/waste"

            driver.get(page)

            wait = WebDriverWait(driver, 30)

            try:
                # Cookies confirmed working in selenium
                accept_cookies_button = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//button/span[contains(text(), 'I Accept Cookies')]",
                        )
                    )
                )
                accept_cookies_button.click()
            except:
                print(
                    "Accept cookies banner not found or clickable within the specified time."
                )
                pass

            postcode_input = wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[@id="postcode"]'))
            )

            postcode_input.send_keys(user_postcode)

            postcode_go_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//input[@id="go"]'))
            )

            postcode_go_button.click()

            # Wait for the select address drop down to be present
            select_address_input = wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[@id="address"]'))
            )

            select_address_input.click()
            time.sleep(2)

            select_address_input_item = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//li[contains(text(), '{user_poan}')]")
                )
            )

            select_address_input_item.click()

            address_continue_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//input[@value="Continue"]'))
            )

            address_continue_button.click()

            your_collections_heading = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h2[contains(text(), 'Your collections')]")
                )
            )

            results_page = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='waste__collections']")
                )
            )

            soup = BeautifulSoup(results_page.get_attribute("innerHTML"), "html.parser")

            data = {"bins": []}
            output_date_format = "%d/%m/%Y"
            input_date_format = "%A, %d %B %Y"  # Expect: Thursday, 17 April 2025

            # Each bin section is within a waste-service-wrapper div
            collection_panels = soup.find_all("div", class_="waste-service-wrapper")

            for panel in collection_panels:
                try:
                    # Bin type
                    bin_type_tag = panel.find("h3", class_="waste-service-name")
                    if not bin_type_tag:
                        continue
                    bin_type = bin_type_tag.get_text(strip=True)

                    # Get 'Next collection' date
                    rows = panel.find_all("div", class_="govuk-summary-list__row")
                    next_collection = None
                    for row in rows:
                        key = row.find("dt", class_="govuk-summary-list__key")
                        value = row.find("dd", class_="govuk-summary-list__value")
                        if key and value and "Next collection" in key.get_text():
                            raw_date = " ".join(value.get_text().split())

                            # ✅ Remove st/nd/rd/th suffix from the day (e.g. 17th → 17)
                            cleaned_date = re.sub(
                                r"(\d{1,2})(st|nd|rd|th)", r"\1", raw_date
                            )
                            next_collection = cleaned_date
                            break

                    if not next_collection:
                        continue

                    print(f"Found next collection for {bin_type}: '{next_collection}'")

                    parsed_date = datetime.strptime(next_collection, input_date_format)
                    formatted_date = parsed_date.strftime(output_date_format)

                    data["bins"].append(
                        {
                            "type": bin_type,
                            "collectionDate": formatted_date,
                        }
                    )

                except Exception as e:
                    print(
                        f"Error processing panel for bin '{bin_type if 'bin_type' in locals() else 'unknown'}': {e}"
                    )

            # Sort the data
            data["bins"].sort(
                key=lambda x: datetime.strptime(x["collectionDate"], output_date_format)
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
