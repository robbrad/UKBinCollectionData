from bs4 import BeautifulSoup

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
            data = {"bins": []}

            # Loop through the items on the page and build a JSON object for ingestion
            for item in soup.select(".t-MediaList-item"):
                for value in item.select(".t-MediaList-body"):
                    dict_data = {
                        "type": value.select("span")[1].get_text(strip=True).title(),
                        "collectionDate": datetime.strptime(
                            value.select(".t-MediaList-desc")[0].get_text(strip=True),
                            "%A, %d %B, %Y",
                        ).strftime(date_format),
                    }
                    data["bins"].append(dict_data)

            return data
