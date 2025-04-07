from time import sleep

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            house_number = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(house_number)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get("https://www.ceredigion.gov.uk/resident/bins-recycling/")

            try:
                accept_cookies = WebDriverWait(driver, timeout=10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[@id='ccc-reject-settings']")
                    )
                )
                accept_cookies.click()
            except:
                print(
                    "Accept cookies banner not found or clickable within the specified time."
                )
                pass

            # Wait for postcode entry box
            postcode_search = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(text(), 'Postcode Search')]")
                )
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", postcode_search)

            sleep(2)  # Wait for the element to be in view

            postcode_search.click()

            postcode_entry_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@data-ebv-desc='Postcode']")
                )
            )

            # Enter postcode
            postcode_entry_box.send_keys(user_postcode)

            postcode_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@value='Find Address']")
                )
            )

            postcode_button.click()

            address_dropdown = Select(
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//select[@data-ebv-desc='Select Address']")
                    )
                )
            )

            address_dropdown.select_by_visible_text(house_number)

            address_next_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@value='Next']"))
            )

            address_next_button.click()

            result = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//form[contains(., 'Next collection:')]")
                )
            )

            # Make a BS4 object
            soup = BeautifulSoup(
                result.get_attribute("innerHTML"), features="html.parser"
            )

            data = {"bins": []}

            # Find all panels containing collection info
            collection_panels = soup.find_all("div", class_="eb-OL2RoeVH-panel")

            for panel in collection_panels:
                try:
                    # Extract the 'Next collection' date string
                    next_text = panel.find_all("span")[-1].text.strip()
                    match = re.search(
                        r"Next collection:\s*(\w+day)\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)",
                        next_text,
                    )
                    if not match:
                        continue

                    _, day, month = match.groups()
                    year = (
                        datetime.now().year
                    )  # You could enhance this to calculate the correct year if needed
                    full_date = f"{day} {month} {year}"

                    collection_date = datetime.strptime(full_date, "%d %B %Y").strftime(
                        date_format
                    )

                    # Now get all bin types in the sibling image blocks
                    bin_image_blocks = panel.find_next_siblings(
                        "div", class_="waste_image"
                    )
                    for block in bin_image_blocks:
                        label = block.find("span")
                        if label:
                            bin_type = label.text.strip()
                            dict_data = {
                                "type": bin_type,
                                "collectionDate": collection_date,
                            }
                            data["bins"].append(dict_data)
                except Exception as e:
                    print(f"Skipping one panel due to: {e}")

            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
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
