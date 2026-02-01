import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
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
        driver = None
        try:
            data = {"bins": []}
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver with user agent to bypass Cloudflare
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get(
                "https://www.gateshead.gov.uk/article/3150/Bin-collection-day-checker"
            )

            # Wait for initial page load
            WebDriverWait(driver, 30).until(
                lambda d: "Just a moment" not in d.title and d.title != ""
            )

            # Additional wait for page to fully load after Cloudflare
            time.sleep(3)
            
            # Try to accept cookies if the banner appears
            try:
                accept_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.NAME, "acceptall"))
                )
                accept_button.click()
                time.sleep(2)
            except:
                pass

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.ID, "BINCOLLECTIONCHECKER_ADDRESSSEARCH_ADDRESSLOOKUPPOSTCODE")
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "BINCOLLECTIONCHECKER_ADDRESSSEARCH_ADDRESSLOOKUPSEARCH")
                )
            )
            findAddress.click()

            # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//select[@id='BINCOLLECTIONCHECKER_ADDRESSSEARCH_ADDRESSLOOKUPADDRESS']//option[contains(., '"
                        + user_paon
                        + "')]",
                    )
                )
            ).click()

            # Handle Cloudflare challenge that appears after address selection
            try:
                # Check for Cloudflare Turnstile "Verify you are human" checkbox
                turnstile_checkbox = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='checkbox']"))
                )
                turnstile_checkbox.click()
                # Wait for verification to complete
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "success"))
                )
                time.sleep(3)
            except:
                pass  # No Turnstile challenge or already completed

            # Wait for page to change after address selection and handle dynamic loading
            time.sleep(5)
            
            # Wait for any content that indicates results are loaded
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'collection') or contains(text(), 'Collection') or contains(text(), 'bin') or contains(text(), 'Bin') or contains(text(), 'refuse') or contains(text(), 'Refuse') or contains(text(), 'recycling') or contains(text(), 'Recycling')]"))
                )
            except:
                # If no specific text found, just wait for page to stabilize
                time.sleep(10)

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Save page source for debugging
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            
            # Find the bin collections table
            table = soup.find("table", class_="bincollections__table")
            
            if not table:
                raise ValueError("Could not find bin collections table in page source - saved debug_page.html")
            
            # Get current year for date parsing
            current_year = datetime.now().year
            current_month = None
            
            # Parse the table rows
            rows = table.find_all("tr")
            for row in rows:
                # Check if this is a month header row
                th = row.find("th")
                if th and th.get("colspan"):
                    # This is a month header
                    current_month = th.get_text(strip=True)
                    continue
                
                # Parse data rows
                cells = row.find_all("td")
                if len(cells) >= 3:
                    # Extract day, weekday, and bin type(s)
                    day = cells[0].get_text(strip=True)
                    weekday = cells[1].get_text(strip=True)
                    bin_cell = cells[2]
                    
                    # Extract all bin types from the cell (may contain multiple links)
                    bin_links = bin_cell.find_all("a")
                    bin_types = []
                    for link in bin_links:
                        bin_type = link.get_text(strip=True)
                        if bin_type:
                            bin_types.append(bin_type)
                    
                    # If no links found, try getting text directly
                    if not bin_types:
                        bin_text = bin_cell.get_text(strip=True)
                        if bin_text:
                            bin_types = [bin_text]
                    
                    # Parse the date
                    if current_month and day:
                        try:
                            # Construct date string: "day month year"
                            date_str = f"{day} {current_month} {current_year}"
                            parsed_date = datetime.strptime(date_str, "%d %B %Y")
                            
                            # If the parsed date is more than 6 months in the past, it's probably next year
                            if (datetime.now() - parsed_date).days > 180:
                                parsed_date = parsed_date.replace(year=current_year + 1)
                            
                            # Add each bin type as a separate entry
                            for bin_type in bin_types:
                                dict_data = {
                                    "type": bin_type,
                                    "collectionDate": parsed_date.strftime(date_format),
                                }
                                data["bins"].append(dict_data)
                        except Exception as e:
                            print(f"Error parsing date for row: {e}")
                            continue

            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
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
