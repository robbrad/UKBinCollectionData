import re
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)
        headless = kwargs.get("headless")
        web_driver = kwargs.get("web_driver")

        url = f"https://www.durham.gov.uk/bincollections?uprn={uprn}"

        driver = create_webdriver(web_driver, headless, None, __name__)
        try:
            driver.get(url)

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".binsrubbish, .binsrecycling")
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")
        finally:
            driver.quit()

        data = {"bins": []}

        for bin_type in ["rubbish", "recycling", "gardenwaste"]:
            bin_info = soup.find(class_=f"bins{bin_type}")

            if bin_info:
                collection_text = bin_info.get_text(strip=True)

                if collection_text:
                    results = re.search(r"\d\d? [A-Za-z]+ \d{4}", collection_text)
                    if results:
                        date = datetime.strptime(results[0], "%d %B %Y")
                        data["bins"].append(
                            {
                                "type": bin_type,
                                "collectionDate": date.strftime(date_format),
                            }
                        )

        return data
