import re
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            user_postcode = kwargs.get("postcode")
            if not user_postcode:
                raise ValueError("No postcode provided.")
            check_postcode(user_postcode)

            user_uprn = kwargs.get("uprn")
            check_uprn(user_uprn)

            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            driver = create_webdriver(web_driver, headless, None, __name__)
            
            # Go directly to the form URL
            driver.get("https://myangus.angus.gov.uk/service/Bin_collection_dates_V3")

            wait = WebDriverWait(driver, 20)
            
            # Wait for iframe to be present and switch to it
            iframe = wait.until(EC.presence_of_element_located((By.ID, "fillform-frame-1")))
            driver.switch_to.frame(iframe)

            # Wait for page to load
            import time
            time.sleep(3)

            # Try to find the postcode input with different selectors
            try:
                postcode_input = wait.until(EC.element_to_be_clickable((By.ID, "searchString")))
            except TimeoutException:
                # Try alternative selectors
                try:
                    postcode_input = driver.find_element(By.NAME, "searchString")
                except NoSuchElementException:
                    try:
                        postcode_input = driver.find_element(By.CSS_SELECTOR, "input[type='text']")
                    except NoSuchElementException:
                        # Print page source for debugging
                        print("Page source:", driver.page_source[:1000])
                        raise ValueError("Could not find postcode input field")
            postcode_input.clear()
            postcode_input.send_keys(user_postcode)
            
            # Find and click the search button
            try:
                submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Search')]")
                submit_btn.click()
            except:
                try:
                    submit_btn = driver.find_element(By.XPATH, "//input[@type='submit']")
                    submit_btn.click()
                except:
                    postcode_input.send_keys(Keys.TAB)
                    postcode_input.send_keys(Keys.ENTER)

            # Wait for address dropdown to be present
            address_dropdown = wait.until(EC.presence_of_element_located((By.ID, "customerAddress")))
            
            # Wait for dropdown options to populate with extended timeout
            try:
                WebDriverWait(driver, 30).until(
                    lambda d: len(d.find_element(By.ID, "customerAddress").find_elements(By.TAG_NAME, "option")) > 1
                )
            except TimeoutException:
                options = address_dropdown.find_elements(By.TAG_NAME, "option")
                raise ValueError(f"Dropdown only has {len(options)} options after 30s wait")
            
            # Select the UPRN from dropdown
            dropdown = Select(address_dropdown)
            dropdown.select_by_value(user_uprn)

            # Wait for results to appear
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "span.fieldInput.content.html.non-input")
                )
            )
            
            # Wait additional time for JavaScript to populate the data
            import time
            time.sleep(15)  # Wait 15 seconds for dynamic content to load

            # Parse the results
            soup = BeautifulSoup(driver.page_source, "html.parser")
            bin_data = {"bins": []}
            current_date = datetime.now()
            current_formatted_date = None

            spans = soup.select("span.fieldInput.content.html.non-input")

            for i, span in enumerate(spans):
                try:
                    # Look for date in <u> tags
                    date_tag = next(
                        (u for u in span.find_all("u") if u and u.text.strip()),
                        None
                    )
                    bin_type_tag = span.find("b")

                    if date_tag:
                        raw_date = date_tag.text.strip().replace(",", "")
                        full_date_str = f"{raw_date} {current_date.year}"
                        full_date_str = re.sub(r"\s+", " ", full_date_str)

                        try:
                            parsed_date = datetime.strptime(full_date_str, "%A %d %B %Y")
                            if parsed_date.date() < current_date.date():
                                parsed_date = parsed_date.replace(year=current_date.year + 1)
                            current_formatted_date = parsed_date.strftime("%d/%m/%Y")
                        except ValueError:
                            continue

                    if not current_formatted_date or not bin_type_tag:
                        continue

                    bin_type = bin_type_tag.text.strip()
                    if not bin_type:
                        continue

                    # Optional seasonal override
                    try:
                        overrides_dict = get_seasonal_overrides()
                        if current_formatted_date in overrides_dict:
                            current_formatted_date = overrides_dict[current_formatted_date]
                    except Exception:
                        pass

                    bin_data["bins"].append({
                        "type": bin_type,
                        "collectionDate": current_formatted_date
                    })

                except Exception:
                    continue

            if not bin_data["bins"]:
                raise ValueError("No bin data found.")
            
            return bin_data

        except Exception as e:
            print(f"An error occurred: {e}")
            raise

        finally:
            if driver:
                driver.quit()