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

    def parse_data(self, page: str, **kwargs) -> dict:
        # Make a BS4 object
        print(f"Arguments are f{kwargs}")
        driver = None
        try:
            page = kwargs["url"]
            street_name = kwargs.get("house_number")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")

            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(page)

            wait = WebDriverWait(driver, 60)

            dismiss_cookie_banner = wait.until(
                EC.visibility_of_element_located(
                    (By.ID, "ccc-dismiss-button")
                )
            )

            dismiss_cookie_banner.send_keys(Keys.ENTER)

            inputElement_postcodesearch = wait.until(
                EC.visibility_of_element_located(
                    (By.ID, "Street")
                )
            )

            inputElement_postcodesearch.send_keys(street_name)

            main_content_submit_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, ".//div[@id='maincontent']//input[@type='submit']")
                )
            )

            main_content_submit_button.send_keys(Keys.ENTER)

            collection_row = driver.find_element(
                By.CLASS_NAME, "lb-table-row-highlight"
            )

            table = driver.find_element(By.XPATH, ".//div[@id='maincontent']//table")
            table_rows = table.find_elements(by=By.TAG_NAME, value="tr")
            headerRow = table_rows[0]
            table_info_row = table_rows[1]

            bin_types = headerRow.find_elements(by=By.TAG_NAME, value ="th")[2:]
            collection_days = table_info_row.find_elements(by=By.TAG_NAME, value ="td")[2:]

            for index, bin in enumerate(bin_types):
                if index == 0:
                    next_collection_date = collection_days[index].text
                print(f"{bin.text} - {collection_days[index].text}")

            #
            # # Now create a Select object based on the found element
            # dropdown = Select(dropdown_element)
            #
            # # Select the option by visible text
            # dropdown.select_by_visible_text(house_number)
            #
            # results = wait.until(
            #     EC.element_to_be_clickable(
            #         (By.CLASS_NAME, "bin-collection-dates-container")
            #     )
            # )
            #
            # soup = BeautifulSoup(driver.page_source, features="html.parser")
            # soup.prettify()

            # Extract data from the table
            bin_collection_data = []
            # rows = soup.find(
            #     "table", class_="defaultgeneral bin-collection-dates"
            # ).find_all("tr")
            # for row in rows:
            #     cells = row.find_all("td")
            #     if cells:
            #         date_str = cells[0].text.strip()
            #         bin_type = cells[1].text.strip()
            #         # Convert date string to the required format DD/MM/YYYY
            #         date_obj = datetime.strptime(date_str, "%d %B %Y")
            #         date_formatted = date_obj.strftime(date_format)
            #         bin_collection_data.append(
            #             {"collectionDate": date_formatted, "type": bin_type}
            #         )

            # Convert to JSON
            json_data = {"bins": bin_collection_data}

        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return json_data


print("Hello World!")
CouncilClass().parse_data("", url="https://www.richmond.gov.uk/services/waste_and_recycling/collection_days/",
                          house_number="March Road", headless=True)
