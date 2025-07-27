import time
import re
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def get_seasonal_overrides():
    url = "https://www.barnet.gov.uk/recycling-and-waste/bin-collections/find-your-bin-collection-day"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        body_div = soup.find("div", class_="field--name-body")
        if body_div:
            ul_element = body_div.find("ul")
            if ul_element:
                li_elements = ul_element.find_all("li")
                overrides_dict = {}
                for li_element in li_elements:
                    li_text = li_element.text.strip()
                    li_text = re.sub(r"\([^)]*\)", "", li_text).strip()
                    if "Collections for" in li_text and "will be revised to" in li_text:
                        parts = li_text.split("will be revised to")
                        original_date = (
                            parts[0]
                            .replace("Collections for", "")
                            .replace("\xa0", " ")
                            .strip()
                        )
                        revised_date = parts[1].strip()

                        # Extract day and month
                        date_parts = original_date.split()[1:]
                        if len(date_parts) == 2:
                            day, month = date_parts
                            # Ensure original_date has leading zeros for single-digit days
                            day = day.zfill(2)
                            original_date = f"{original_date.split()[0]} {day} {month}"

                        # Store the information in the dictionary
                        overrides_dict[original_date] = revised_date
                return overrides_dict
    return {}


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            user_postcode = kwargs.get("postcode")
            if not user_postcode:
                raise ValueError("No postcode provided.")
            check_postcode(user_postcode)

            user_paon = kwargs.get("paon")
            check_paon(user_paon)
            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            driver = create_webdriver(web_driver, headless, None, __name__)
            page = "https://www.barnet.gov.uk/recycling-and-waste/bin-collections/find-your-bin-collection-day"

            driver.get(page)

            # Handle first cookie banner
            try:
                wait = WebDriverWait(driver, 10)
                accept_cookies_button = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//button[contains(text(), 'Accept additional cookies')]",
                        )
                    )
                )
                driver.execute_script("arguments[0].click();", accept_cookies_button)
            except Exception as e:
                print(f"Cookie banner not found or clickable: {e}")
                pass

            # Click the collection day link
            wait = WebDriverWait(driver, 10)
            find_your_collection_button = wait.until(
                EC.element_to_be_clickable(
                    (By.LINK_TEXT, "Find your household collection day")
                )
            )
            driver.execute_script(
                "arguments[0].scrollIntoView();", find_your_collection_button
            )
            time.sleep(1)
            driver.execute_script("arguments[0].click();", find_your_collection_button)

            # Handle second cookie banner
            try:
                accept_cookies = WebDriverWait(driver, timeout=10).until(
                    EC.presence_of_element_located((By.ID, "epdagree"))
                )
                driver.execute_script("arguments[0].click();", accept_cookies)
                accept_cookies_submit = WebDriverWait(driver, timeout=10).until(
                    EC.presence_of_element_located((By.ID, "epdsubmit"))
                )
                driver.execute_script("arguments[0].click();", accept_cookies_submit)
            except Exception as e:
                print(f"Second cookie banner not found or clickable: {e}")
                pass

            # Enter postcode
            postcode_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[aria-label="Postcode"]')
                )
            )
            postcode_input.send_keys(user_postcode)

            # Click find address
            find_address_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[value="Find address"]'))
            )
            driver.execute_script("arguments[0].scrollIntoView();", find_address_button)
            driver.execute_script("arguments[0].click();", find_address_button)

            time.sleep(5)
            # Wait for address dropdown
            select_address_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.ID,
                        "MainContent_CUSTOM_FIELD_808562d4b07f437ea751317cabd19d9eeaf8742f49cb4f7fa9bef99405b859f2",
                    )
                )
            )

            # Select address based on postcode and house number
            select = Select(select_address_input)
            selected = False
            
            for addr_option in select.options:
                if not addr_option.text or addr_option.text == "Please Select...":
                    continue
                    
                option_text = addr_option.text.upper()
                postcode_upper = user_postcode.upper()
                paon_str = str(user_paon).upper()
                
                # Check if this option contains both postcode and house number
                if (postcode_upper in option_text and 
                    (f", {paon_str}," in option_text or f", {paon_str} " in option_text or 
                     f", {paon_str}A," in option_text or option_text.endswith(f", {paon_str}"))):
                    select.select_by_value(addr_option.get_attribute('value'))
                    selected = True
                    break
            
            if not selected:
                raise ValueError(f"Address not found for postcode {user_postcode} and house number {user_paon}")

            time.sleep(5)
            
            # Wait for bin collection data to appear anywhere on the page
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(text(), 'Next collection') or contains(text(), 'collection date')]")
                    )
                )
            except:
                raise ValueError("Could not find bin collection data on the page")

            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Handle seasonal overrides
            try:
                overrides_dict = get_seasonal_overrides()
            except Exception as e:
                overrides_dict = {}

            # Look for bin collection data anywhere on the page
            bin_data = {"bins": []}
            
            # Find all divs that contain "Next collection date:"
            collection_divs = soup.find_all("div", string=re.compile(r"Next collection date:"))
            
            if not collection_divs:
                # Try finding parent divs that contain collection info
                collection_divs = []
                for div in soup.find_all("div"):
                    if div.get_text() and "Next collection date:" in div.get_text():
                        collection_divs.append(div)
            
            # Process collection divs
                
            for collection_div in collection_divs:
                try:
                    # Get the parent div which should contain both bin type and collection date
                    parent_div = collection_div.parent if collection_div.parent else collection_div
                    full_text = parent_div.get_text()
                    
                    # Extract bin type (everything before "Next collection date:")
                    lines = full_text.split('\n')
                    bin_type = "Unknown"
                    collection_date_string = ""
                    
                    for i, line in enumerate(lines):
                        line = line.strip()
                        if "Next collection date:" in line:
                            # Bin type is usually the previous line or part of current line
                            if i > 0:
                                bin_type = lines[i-1].strip()
                            
                            # Extract date from current line
                            date_match = re.search(r"Next collection date:\s+(.*)", line)
                            if date_match:
                                collection_date_string = date_match.group(1).strip().replace(",", "")
                            break
                    
                    if collection_date_string:
                        if collection_date_string in overrides_dict:
                            collection_date_string = overrides_dict[collection_date_string]

                        current_date = datetime.now()
                        parsed_date = datetime.strptime(
                            collection_date_string + f" {current_date.year}", "%A %d %B %Y"
                        )
                        
                        # Check if the parsed date is in the past
                        if parsed_date.date() < current_date.date():
                            parsed_date = parsed_date.replace(year=current_date.year + 1)
                        
                        formatted_date = parsed_date.strftime("%d/%m/%Y")
                        contains_date(formatted_date)
                        
                        bin_info = {"type": bin_type, "collectionDate": formatted_date}
                        bin_data["bins"].append(bin_info)
                        
                except Exception as e:
                    pass  # Skip problematic divs
                    continue
                        
            if not bin_data["bins"]:
                # Some addresses may not have bin collection data available
                print("No bin collection data found for this address")
                bin_data = {"bins": []}

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        
        return bin_data