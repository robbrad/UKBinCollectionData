from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
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
            data = {"bins": []}
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            user_uprn = kwargs.get("uprn")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(kwargs.get("url"))

            # Click "Check now" button
            check_now_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Check now')]"))
            )
            check_now_button.click()

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "postcodeSearch"))
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click Find button
            find_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Find')]"))
            )
            find_button.click()

            # Wait for the address dropdown and select by UPRN
            if user_uprn:
                address_option = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, f"//option[@value='{user_uprn}']"))
                )
                address_option.click()
            else:
                # Fallback to selecting by address text
                address_option = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//select[@id='addressSelect']//option[contains(., '{user_paon}')]")
                    )
                )
                address_option.click()

            # Wait a moment for the page to update after address selection
            import time
            time.sleep(2)

            # Wait for collection information to appear - try multiple possible selectors
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Your next collections')]"))
                )
            except:
                # Alternative wait for collection data structure
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'ant-row') and contains(@class, 'd-flex')]//h3[@class='text-white']"))
                )

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            
            # Find all collection items with the specific structure - try multiple class patterns
            collection_items = soup.find_all("div", class_=lambda x: x and "ant-col" in x and "ant-col-xs-12" in x)
            if not collection_items:
                # Fallback to finding items by structure
                collection_items = soup.find_all("div", class_=lambda x: x and "p-2" in x and "d-flex" in x and "flex-column" in x)
            
            current_year = datetime.now().year
            current_month = datetime.now().month

            for item in collection_items:
                # Extract bin type from h3 element
                bin_type_elem = item.find("h3", class_="text-white")
                # Extract date from div with specific classes
                date_elem = item.find("div", class_="text-white fw-bold")
                
                if bin_type_elem and date_elem:
                    bin_type = bin_type_elem.get_text().strip()
                    date_text = date_elem.get_text().strip()
                    
                    try:
                        collection_date = datetime.strptime(date_text, "%A %d %B")
                        if (current_month > 10) and (collection_date.month < 3):
                            collection_date = collection_date.replace(year=(current_year + 1))
                        else:
                            collection_date = collection_date.replace(year=current_year)

                        dict_data = {
                            "type": bin_type,
                            "collectionDate": collection_date.strftime("%d/%m/%Y"),
                        }
                        data["bins"].append(dict_data)
                    except ValueError:
                        continue

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
