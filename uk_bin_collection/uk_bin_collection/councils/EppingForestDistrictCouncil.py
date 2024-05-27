from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from uk_bin_collection.uk_bin_collection.common import date_format

class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        postcode = kwargs.get('postcode', '')
        web_driver = kwargs.get("web_driver")
        headless = kwargs.get("headless")
        
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        driver = create_webdriver(web_driver, headless)

        try:
            driver.get(f"https://eppingforestdc.maps.arcgis.com/apps/instant/lookup/index.html?appid=bfca32b46e2a47cd9c0a84f2d8cdde17&find={postcode}")
            wait = WebDriverWait(driver, 10)
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".esri-feature-content")))
            html_content = driver.page_source
            
            soup = BeautifulSoup(html_content, 'html.parser')
            bin_info_divs = soup.select(".esri-feature-content p")
            data = {"bins": []}
            for div in bin_info_divs:
                if 'collection day is' in div.text:
                    bin_type, date_str = div.text.split(' collection day is ')
                    bin_dates = datetime.strptime(date_str.strip(), '%d/%m/%Y').strftime(date_format)
                    data["bins"].append({"type": bin_type.strip(), "collectionDate": bin_dates})
            
            return data
        finally:
            driver.quit()
