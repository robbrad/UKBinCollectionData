import time
import re
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

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
            page = "https://www.angus.gov.uk/bins_litter_and_recycling/bin_collection_days"

            driver.get(page)

            wait = WebDriverWait(driver, 10)
            accept_cookies_button = wait.until(
                EC.element_to_be_clickable((By.ID, "ccc-recommended-settings"))
            )
            accept_cookies_button.click()

            find_your_collection_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[2]/div[2]/div/div/section/div[2]/div/article/div/div/p[2]/a")
                )
            )
            find_your_collection_button.click()

            iframe = wait.until(EC.presence_of_element_located((By.ID, "fillform-frame-1")))
            driver.switch_to.frame(iframe)

            postcode_input = wait.until(EC.presence_of_element_located((By.ID, "searchString")))
            postcode_input.send_keys(user_postcode + Keys.TAB + Keys.ENTER)

            time.sleep(15)

            select_elem = wait.until(EC.presence_of_element_located((By.ID, "customerAddress")))
            WebDriverWait(driver, 10).until(
                lambda d: len(select_elem.find_elements(By.TAG_NAME, "option")) > 1
            )
            dropdown = Select(select_elem)
            dropdown.select_by_value(user_uprn)

            time.sleep(10)

            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "span.fieldInput.content.html.non-input"))
            )

            soup = BeautifulSoup(driver.page_source, "html.parser")
            bin_data = {"bins": []}
            current_date = datetime.now()
            current_formatted_date = None

            spans = soup.select("span.fieldInput.content.html.non-input")
            print(f"Found {len(spans)} bin info spans.")

            for i, span in enumerate(spans):
                try:
                    # Look for any non-empty <u> tag recursively
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
                            print(f"[{i}] Parsed date: {current_formatted_date}")
                        except ValueError as ve:
                            print(f"[{i}] Could not parse date: '{full_date_str}' - {ve}")
                            continue
                    else:
                        print(f"[{i}] No date tag found, using last valid date: {current_formatted_date}")

                    if not current_formatted_date:
                        print(f"[{i}] No current date to associate bin type with — skipping.")
                        continue

                    if not bin_type_tag or not bin_type_tag.text.strip():
                        print(f"[{i}] No bin type found — skipping.")
                        continue

                    bin_type = bin_type_tag.text.strip()

                    # Optional seasonal override
                    try:
                        overrides_dict = get_seasonal_overrides()
                        if current_formatted_date in overrides_dict:
                            current_formatted_date = overrides_dict[current_formatted_date]
                    except Exception:
                        pass

                    print(f"[{i}] Found bin: {bin_type} on {current_formatted_date}")

                    bin_data["bins"].append({
                        "type": bin_type,
                        "collectionDate": current_formatted_date
                    })

                except Exception as inner_e:
                    print(f"[{i}] Skipping span due to error: {inner_e}")
                    continue

                except Exception as inner_e:
                    print(f"Skipping span due to error: {inner_e}")
                    continue

            if not bin_data["bins"]:
                raise ValueError("No bin data found.")

            print(bin_data)
            
            return bin_data

        except Exception as e:
            print(f"An error occurred: {e}")
            raise

        finally:
            if driver:
                driver.quit()