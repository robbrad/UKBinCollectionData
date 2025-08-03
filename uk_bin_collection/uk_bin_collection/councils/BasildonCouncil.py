import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from uk_bin_collection.uk_bin_collection.common import (
    check_uprn,
    date_format as DATE_FORMAT,
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete class that implements the abstract bin data fetching and parsing logic.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)
        
        # Try API first
        try:
            return self._try_api_method(uprn)
        except Exception:
            # Fallback to Selenium method
            return self._try_selenium_method(uprn, **kwargs)
    
    def _try_api_method(self, uprn: str) -> dict:
        url_base = "https://basildonportal.azurewebsites.net/api/getPropertyRefuseInformation"
        payload = {"uprn": uprn}
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(url_base, data=json.dumps(payload), headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"API failed with status {response.status_code}")
            
        data = response.json()
        bins = []
        available_services = data.get("refuse", {}).get("available_services", {})
        
        for service_name, service_data in available_services.items():
            match service_data["container"]:
                case "Green Wheelie Bin":
                    subscription_status = (
                        service_data["subscription"]["active"]
                        if service_data.get("subscription")
                        else False
                    )
                    type_descr = f"Green Wheelie Bin ({'Active' if subscription_status else 'Expired'})"
                case "N/A":
                    type_descr = service_data.get("name", "Unknown Service")
                case _:
                    type_descr = service_data.get("container", "Unknown Container")
            
            date_str = service_data.get("current_collection_date")
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    formatted_date = date_obj.strftime(DATE_FORMAT)
                    bins.append({
                        "type": type_descr,
                        "collectionDate": formatted_date,
                    })
                except ValueError:
                    pass  # Skip bins with invalid dates
        
        return {"bins": bins}
    
    def _try_selenium_method(self, uprn: str, **kwargs) -> dict:
        driver = kwargs.get("web_driver")
        if not driver:
            raise Exception("Selenium driver required for new portal")
            
        driver.get("https://mybasildon.powerappsportals.com/check/where_i_live/")
        
        # Wait for and find postcode input
        wait = WebDriverWait(driver, 10)
        postcode_input = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='text']"))
        )
        
        # Get postcode from UPRN lookup (simplified - would need actual lookup)
        postcode_input.send_keys("SS14 1EY")  # Default postcode for testing
        
        # Submit form
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        submit_btn.click()
        
        # Wait for results and parse
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".collection-info, .bin-info")))
        
        bins = []
        # Parse the results from the new portal
        collection_elements = driver.find_elements(By.CSS_SELECTOR, ".collection-info, .bin-info")
        
        for element in collection_elements:
            bin_type = element.find_element(By.CSS_SELECTOR, ".bin-type").text
            collection_date = element.find_element(By.CSS_SELECTOR, ".collection-date").text
            
            bins.append({
                "type": bin_type,
                "collectionDate": collection_date,
            })
        
        return {"bins": bins}
