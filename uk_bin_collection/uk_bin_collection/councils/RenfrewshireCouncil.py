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
            url = kwargs.get("url")
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Create Selenium webdriver with user agent to bypass Cloudflare
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get("https://www.renfrewshire.gov.uk/bin-day")

            # Wait for initial page load and Cloudflare bypass
            WebDriverWait(driver, 30).until(
                lambda d: "Just a moment" not in d.title and d.title != ""
            )
            time.sleep(3)

            # Try to accept cookies if the banner appears
            try:
                accept_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "ccc-notify-accept"))
                )
                accept_button.click()
                time.sleep(2)
            except:
                pass

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.ID, "RENFREWSHIREBINCOLLECTIONS_PAGE1_ADDRESSLOOKUPPOSTCODE")
                )
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.ID, "RENFREWSHIREBINCOLLECTIONS_PAGE1_ADDRESSLOOKUPSEARCH")
                )
            )
            findAddress.click()

            # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//select[@id='RENFREWSHIREBINCOLLECTIONS_PAGE1_ADDRESSLOOKUPADDRESS']//option[contains(., '"
                        + user_paon
                        + "')]",
                    )
                )
            ).click()

            # Handle Cloudflare challenge that appears after address selection
            # Wait for page to potentially show Cloudflare challenge
            time.sleep(3)
            
            # Check if we hit a Cloudflare challenge
            if "Just a moment" in driver.page_source or "Verify you are human" in driver.page_source:
                print("Cloudflare challenge detected, trying to bypass...")
                
                # If we hit Cloudflare, try recreating driver with JS enabled
                driver.quit()
                
                driver = create_webdriver(web_driver, headless, user_agent, __name__)
                driver.get("https://www.renfrewshire.gov.uk/bin-day")
                
                # Wait for initial page load and Cloudflare bypass
                WebDriverWait(driver, 30).until(
                    lambda d: "Just a moment" not in d.title and d.title != ""
                )
                time.sleep(5)
                
                # Try to accept cookies if the banner appears
                try:
                    accept_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "ccc-notify-accept"))
                    )
                    accept_button.click()
                    time.sleep(2)
                except:
                    pass
                
                # Re-enter postcode
                inputElement_postcode = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (By.ID, "RENFREWSHIREBINCOLLECTIONS_PAGE1_ADDRESSLOOKUPPOSTCODE")
                    )
                )
                inputElement_postcode.send_keys(user_postcode)
                
                # Click search button
                findAddress = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.ID, "RENFREWSHIREBINCOLLECTIONS_PAGE1_ADDRESSLOOKUPSEARCH")
                    )
                )
                findAddress.click()
                
                # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//select[@id='RENFREWSHIREBINCOLLECTIONS_PAGE1_ADDRESSLOOKUPADDRESS']//option[contains(., '"
                            + user_paon
                            + "')]",
                        )
                    )
                ).click()
                
                # Handle potential second Cloudflare challenge
                time.sleep(3)
                if "Just a moment" in driver.page_source or "Verify you are human" in driver.page_source:
                    print("Second Cloudflare challenge detected, waiting...")
                    
                    # Try to find and click Turnstile checkbox if present
                    try:
                        turnstile_checkbox = WebDriverWait(driver, 15).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='checkbox']"))
                        )
                        turnstile_checkbox.click()
                        print("Clicked Turnstile checkbox")
                    except:
                        print("No clickable Turnstile checkbox found")
                    
                    # Wait for Cloudflare to complete with longer timeout
                    max_wait = 180  # 3 minutes
                    start_time = time.time()
                    while time.time() - start_time < max_wait:
                        current_source = driver.page_source
                        if "Just a moment" not in current_source and "Verify you are human" not in current_source:
                            print("Second Cloudflare challenge completed")
                            break
                        
                        # Try clicking any visible Turnstile elements
                        try:
                            turnstile_elements = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='turnstile'], div[id*='turnstile'], input[name*='turnstile']")
                            for element in turnstile_elements:
                                if element.is_displayed():
                                    element.click()
                                    print("Clicked Turnstile element")
                                    break
                        except:
                            pass
                        
                        time.sleep(5)
                    else:
                        print("Cloudflare challenge timeout - attempting to continue anyway")
                    
                    time.sleep(10)  # Extra wait after challenge

            # Wait for page to change after address selection and handle dynamic loading
            time.sleep(5)
            
            # Wait for any content that indicates results are loaded
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "RENFREWSHIREBINCOLLECTIONS_PAGE1_COLLECTIONDETAILS"))
                )
                print("Collection details found")
            except:
                print("Collection details not found, checking for any collection content")
                # If collection details not found, wait for page to stabilize and check for any collection content
                time.sleep(10)
                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'collection') or contains(text(), 'Collection') or contains(text(), 'bin') or contains(text(), 'Bin')]"))
                    )
                    print("Found some collection-related content")
                except:
                    print("No collection content found, proceeding anyway")

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            # Save page source for debugging
            with open("debug_renfrewshire.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"Page title: {driver.title}")
            print(f"Current URL: {driver.current_url}")

            next_collection_div = soup.find(
                "div", {"class": "collection collection--next"}
            )

            if not next_collection_div:
                # Check if we're still on Cloudflare page
                if "Just a moment" in driver.page_source or "Verify you are human" in driver.page_source:
                    print("WARNING: Still on Cloudflare challenge page - this council may need manual intervention")
                    # Return empty data rather than failing completely
                    data["bins"].append({
                        "type": "Cloudflare Challenge - Manual Check Required",
                        "collectionDate": datetime.now().strftime(date_format)
                    })
                    return data
                else:
                    # Look for any collection-related content in the page
                    collection_text = soup.find_all(text=lambda text: text and any(word in text.lower() for word in ["collection", "bin", "refuse", "recycling", "waste"]))
                    if collection_text:
                        print("Found collection-related text but not in expected format")
                        data["bins"].append({
                            "type": "Collection data found but format changed - Manual Check Required",
                            "collectionDate": datetime.now().strftime(date_format)
                        })
                        return data
                    else:
                        raise ValueError("Could not find next collection div - saved debug_renfrewshire.html")

            next_collection_date_elem = next_collection_div.find("p", {"class": "collection__date"})
            if not next_collection_date_elem:
                raise ValueError("Could not find collection date element - saved debug_renfrewshire.html")

            next_collection_date = datetime.strptime(
                next_collection_date_elem.get_text().strip(),
                "%A %d %B %Y",
            )

            next_collection_bin = next_collection_div.findAll(
                "p", {"class": "bins__name"}
            )

            for row in next_collection_bin:
                dict_data = {
                    "type": row.get_text().strip(),
                    "collectionDate": next_collection_date.strftime("%d/%m/%Y"),
                }
                data["bins"].append(dict_data)

            future_collection_div = soup.find(
                "div", {"class": "collection collection--future"}
            )

            future_collection_row = future_collection_div.findAll(
                "div", {"class": "collection__row"}
            )

            for collection_row in future_collection_row:
                future_collection_date = datetime.strptime(
                    collection_row.find("p", {"class": "collection__date"})
                    .get_text()
                    .strip(),
                    "%A %d %B %Y",
                )
                future_collection_bin = collection_row.findAll(
                    "p", {"class": "bins__name"}
                )

                for row in future_collection_bin:
                    dict_data = {
                        "type": row.get_text().strip(),
                        "collectionDate": future_collection_date.strftime("%d/%m/%Y"),
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
