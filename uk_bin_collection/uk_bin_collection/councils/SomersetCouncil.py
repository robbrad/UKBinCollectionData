import datetime

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
<<<<<<< HEAD
        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/87.0.4280.141 Safari/537.36"
        }

        requests.packages.urllib3.disable_warnings()
        with requests.Session() as s:
            # Set Headers
            s.headers = headers

            # Get the first page - This is the Search for property by Post Code page
            resource = s.get(
                "https://iweb.itouchvision.com/portal/f?p=customer:BIN_DAYS:::NO:RP:UID:625C791B4D9301137723E9095361401AE8C03934"
            )
            # Create a BeautifulSoup object from the page's HTML
            soup = BeautifulSoup(resource.text, "html.parser")

            # The page contains a number of values that must be passed into subsequent requests - extract them here
            payload = {
                i["name"]: i.get("value", "") for i in soup.select("input[name]")
            }
            payload2 = {
                i["data-for"]: i.get("value", "")
                for i in soup.select("input[data-for]")
            }
            
            # Check if required form elements exist
            salt_element = soup.select_one('input[id="pSalt"]')
            protected_element = soup.select_one('input[id="pPageItemsProtected"]')
            
            if not salt_element or not protected_element:
                raise Exception("Required form elements not found. The council website may have changed or be unavailable.")
            
            payload_salt = salt_element.get("value")
            payload_protected = protected_element.get("value")

            # Add the PostCode and 'SEARCH' to the payload
            payload["p_request"] = "SEARCH"
            payload["P153_POST_CODE"] = user_postcode

            # Manipulate the lists and build the JSON that must be submitted in further requests - some data is nested
            merged_list = {**payload, **payload2}
            new_list = []
            other_list = {}
            for key in merged_list.keys():
                temp_list = {}
                val = merged_list[key]
                if key in [
                    "P153_UPRN",
                    "P153_TEMP",
                    "P153_SYSDATE",
                    "P0_LANGUAGE",
                    "P153_POST_CODE",
                ]:
                    temp_list = {"n": key, "v": val}
                    new_list.append(temp_list)
                elif key in [
                    "p_flow_id",
                    "p_flow_step_id",
                    "p_instance",
                    "p_page_submission_id",
                    "p_request",
                    "p_reload_on_submit",
                ]:
                    other_list[key] = val
                else:
                    temp_list = {"n": key, "v": "", "ck": val}
                    new_list.append(temp_list)

            json_builder = {
                "pageItems": {
                    "itemsToSubmit": new_list,
                    "protected": payload_protected,
                    "rowVersion": "",
                    "formRegionChecksums": [],
                },
                "salt": payload_salt,
            }
            json_object = json.dumps(json_builder, separators=(",", ":"))
            other_list["p_json"] = json_object

            # Set Referrer header
            s.headers.update(
                {
                    "referer": "https://iweb.itouchvision.com/portal/f?p=customer:BIN_DAYS:::NO:RP:UID:625C791B4D9301137723E9095361401AE8C03934"
                }
            )

            # Generate POST including all the JSON we just built
            s.post(
                "https://iweb.itouchvision.com/portal/wwv_flow.accept", data=other_list
            )

            # The second page on the portal would normally allow you to select your property from a dropdown list of
            # those that are at the postcode entered on the previous page
            # The required cookies are stored within the session so re-use the session to keep them
            resource = s.get(
                "https://iweb.itouchvision.com/portal/itouchvision/r/customer/bin_days"
            )

            # Create a BeautifulSoup object from the page's HTML
            soup = BeautifulSoup(resource.text, "html.parser")

            # The page contains a number of values that must be passed into subsequent requests - extract them here
            payload = {
                i["name"]: i.get("value", "") for i in soup.select("input[name]")
            }
            payload2 = {
                i["data-for"]: i.get("value", "")
                for i in soup.select("input[data-for]")
            }
            
            # Check if required form elements exist
            salt_element = soup.select_one('input[id="pSalt"]')
            protected_element = soup.select_one('input[id="pPageItemsProtected"]')
            
            if not salt_element or not protected_element:
                raise Exception("Required form elements not found. The council website may have changed or be unavailable.")
            
            payload_salt = salt_element.get("value")
            payload_protected = protected_element.get("value")

            # Add the UPRN and 'SUBMIT' to the payload
            payload["p_request"] = "SUBMIT"
            payload["P153_UPRN"] = user_uprn

            # Manipulate the lists and build the JSON that must be submitted in further requests - some data is nested
            merged_list = {**payload, **payload2}
            new_list = []
            other_list = {}
            for key in merged_list.keys():
                temp_list = {}
                val = merged_list[key]
                if key in ["P153_UPRN", "P153_TEMP", "P153_SYSDATE", "P0_LANGUAGE"]:
                    temp_list = {"n": key, "v": val}
                    new_list.append(temp_list)
                elif key in ["P153_ZABY"]:
                    temp_list = {"n": key, "v": "1", "ck": val}
                    new_list.append(temp_list)
                elif key in ["P153_POST_CODE"]:
                    temp_list = {"n": key, "v": user_postcode, "ck": val}
                    new_list.append(temp_list)
                elif key in [
                    "p_flow_id",
                    "p_flow_step_id",
                    "p_instance",
                    "p_page_submission_id",
                    "p_request",
                    "p_reload_on_submit",
                ]:
                    other_list[key] = val
                else:
                    temp_list = {"n": key, "v": "", "ck": val}
                    new_list.append(temp_list)

            json_builder = {
                "pageItems": {
                    "itemsToSubmit": new_list,
                    "protected": payload_protected,
                    "rowVersion": "",
                    "formRegionChecksums": [],
                },
                "salt": payload_salt,
            }

            json_object = json.dumps(json_builder, separators=(",", ":"))
            other_list["p_json"] = json_object

            # Generate POST including all the JSON we just built
            s.post(
                "https://iweb.itouchvision.com/portal/wwv_flow.accept", data=other_list
            )

            # The third and final page on the portal shows the detail of the waste collection services
            # The required cookies are stored within the session so re-use the session to keep them
            resource = s.get(
                "https://iweb.itouchvision.com/portal/itouchvision/r/customer/bin_days"
            )

            # Create a BeautifulSoup object from the page's HTML
            soup = BeautifulSoup(resource.text, "html.parser")
=======
        driver = None
        try:
>>>>>>> master
            data = {"bins": []}
            url = kwargs.get("url")
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_paon(user_paon)
            check_postcode(user_postcode)

            # Use a realistic user agent to help bypass Cloudflare
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            driver = create_webdriver(web_driver, headless, user_agent, __name__)
            driver.get("https://www.somerset.gov.uk/collection-days")

            # Wait for the postcode field to appear then populate it
            inputElement_postcode = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "postcodeSearch"))
            )
            inputElement_postcode.send_keys(user_postcode)

            # Click search button
            findAddress = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "govuk-button"))
            )
            findAddress.click()

            # Wait for the 'Select address' dropdown to appear and select option matching the house name/number
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//select[@id='addressSelect']//option[contains(., '"
                        + user_paon
                        + "')]",
                    )
                )
            ).click()

            # Wait for the collections table to appear
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//h2[contains(@class,'mt-4') and contains(@class,'govuk-heading-s') and normalize-space(.)='Your next collections']",
                    )
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            collections = soup.find_all("div", {"class": "p-2"})

            for collection in collections:
                bin_type = collection.find("h3").get_text()

                next_collection = soup.find("div", {"class": "fw-bold"}).get_text()

                following_collection = soup.find(
                    lambda t: (
                        t.name == "div"
                        and t.get_text(strip=True).lower().startswith("followed by")
                    )
                ).get_text()

                next_collection_date = datetime.strptime(next_collection, "%A %d %B")

                following_collection_date = datetime.strptime(
                    following_collection, "followed by %A %d %B"
                )

                current_date = datetime.now()
                next_collection_date = next_collection_date.replace(
                    year=current_date.year
                )
                following_collection_date = following_collection_date.replace(
                    year=current_date.year
                )

                next_collection_date = get_next_occurrence_from_day_month(
                    next_collection_date
                )

                following_collection_date = get_next_occurrence_from_day_month(
                    following_collection_date
                )

                dict_data = {
                    "type": bin_type,
                    "collectionDate": next_collection_date.strftime(date_format),
                }
                data["bins"].append(dict_data)

                dict_data = {
                    "type": bin_type,
                    "collectionDate": following_collection_date.strftime(date_format),
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
