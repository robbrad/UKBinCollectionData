import time
from datetime import datetime

from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    # Extract data from the table
    def format_date(self, date_str):
        # Convert date format from "Fri 31 May 2024" to "31/05/2024"
        date_match = re.search(r"\d{1,2} \w+ \d{4}", date_str)
        if date_match:
            date_obj = re.search(r"(\d{1,2}) (\w+) (\d{4})", date_match.group(0))
            day = date_obj.group(1).zfill(2)
            month_name = date_obj.group(2)
            month = {
                "January": "01",
                "February": "02",
                "March": "03",
                "April": "04",
                "May": "05",
                "June": "06",
                "July": "07",
                "August": "08",
                "September": "09",
                "October": "10",
                "November": "11",
                "December": "12",
            }[month_name]
            year = date_obj.group(3)
            formatted_date = f"{day}/{month}/{year}"
        else:
            formatted_date = "Unknown Date"
        return formatted_date

    def extract_bin_data(self, article):
        date = article.find("div", class_="binday__cell--day").text.strip()
        bin_type_class = article.get("class")[
            1
        ]  # Assuming the second class indicates the bin type
        bin_type = "black" if "black" in bin_type_class else "silver"
        formatted_date = self.format_date(date)
        return {"type": bin_type, "collectionDate": formatted_date}

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            # Make a BS4 object

            page = "https://pre.southkesteven.gov.uk/BinSearch.aspx"

            user_postcode = kwargs.get("postcode")
            user_uprn = kwargs.get("uprn")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            house_number = kwargs.get("paon")

            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            wait = WebDriverWait(driver, 60)

            inputElement_postcodesearch = wait.until(
                EC.visibility_of_element_located((By.ID, "title"))
            )
            inputElement_postcodesearch.clear()

            inputElement_postcodesearch.send_keys(user_postcode)

            inputElement_postcodesearch_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button/span[text()='Search']"))
            )
            inputElement_postcodesearch_btn.click()

            inputElement_select_address = wait.until(
                EC.element_to_be_clickable((By.ID, "address"))
            )

            # Now create a Select object based on the found element
            dropdown = Select(inputElement_select_address)

            # Select the option by visible text
            dropdown.select_by_visible_text(house_number)

            inputElement_results_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[text()='View your bin days']")
                )
            )
            inputElement_results_btn.click()

            p_element = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//p[contains(text(), 'Your next bin collection date is ')]",
                    )
                )
            )

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            bin_data = []

            # Extract data from the first aside element
            first_aside = soup.find("aside", class_="alert")
            if first_aside:
                next_collection_date = first_aside.find(
                    "span", class_="alert__heading alpha"
                ).text.strip()
                bin_info = {
                    "type": "purple",  # Based on the provided information in the HTML, assuming it's a purple bin day.
                    "collectionDate": self.format_date(next_collection_date),
                }
                bin_data.append(bin_info)

            # Extract data from articles
            articles = soup.find_all("article", class_="binday")
            for article in articles:
                bin_info = self.extract_bin_data(article)
                bin_data.append(bin_info)

            result = {"bins": bin_data}

        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return result
