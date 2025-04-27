import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

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
            user_postcode = kwargs.get("postcode")
            if not user_postcode:
                raise ValueError("No postcode provided.")
            check_postcode(user_postcode)

            user_uprn = kwargs.get("uprn")
            check_uprn(user_uprn)

            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            driver = create_webdriver(web_driver, headless, None, __name__)
            page = "https://www.rugby.gov.uk/check-your-next-bin-day"

            driver.get(page)

            wait = WebDriverWait(driver, 60)
            accept_cookies_button = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.ID,
                        "ccc-recommended-settings",
                    )
                )
            )
            accept_cookies_button.click()

            postcode_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        '//*[@id="_com_placecube_digitalplace_local_waste_portlet_CollectionDayFinderPortlet_postcode"]',
                    )
                )
            )
            postcode_input.send_keys(user_postcode + Keys.TAB + Keys.ENTER)

            time.sleep(5)
            # Wait for address box to be visible
            select_address_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.ID,
                        "_com_placecube_digitalplace_local_waste_portlet_CollectionDayFinderPortlet_uprn",
                    )
                )
            )

            # Select address based
            select = Select(select_address_input)
            for option in select.options:
                if option.get_attribute("value") == str(user_uprn):
                    select.select_by_value(str(user_uprn))
                    break
            else:
                raise ValueError(f"UPRN {user_uprn} not found in address options")

            select_address_input.send_keys(Keys.TAB + Keys.ENTER)

            # Wait for the specified table to be present
            target_table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        '//*[@id="portlet_com_placecube_digitalplace_local_waste_portlet_CollectionDayFinderPortlet"]/div/div/div/div/table',
                    )
                )
            )

            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Initialize bin data dictionary
            bin_data = {"bins": []}

            # Find the table
            table = soup.find("table", class_="table")
            if table:
                # Find all rows in tbody
                rows = table.find("tbody").find_all("tr")

                for row in rows:
                    # Get all cells in the row
                    cells = row.find_all("td")
                    if len(cells) >= 4:  # Ensure we have enough cells
                        bin_type = cells[0].text.strip()
                        next_collection = cells[1].text.strip()
                        following_collection = cells[3].text.strip()

                        # Parse the dates
                        for collection_date in [next_collection, following_collection]:
                            try:
                                # Convert date from "Friday 09 May 2025" format
                                parsed_date = datetime.strptime(
                                    collection_date, "%A %d %B %Y"
                                )
                                formatted_date = parsed_date.strftime("%d/%m/%Y")

                                bin_info = {
                                    "type": bin_type,
                                    "collectionDate": formatted_date,
                                }
                                bin_data["bins"].append(bin_info)
                            except ValueError as e:
                                print(f"Error parsing date {collection_date}: {e}")
            else:
                raise ValueError("Collection data table not found")

            # Sort the collections by date
            bin_data["bins"].sort(
                key=lambda x: datetime.strptime(x["collectionDate"], "%d/%m/%Y")
            )

            print(bin_data)

        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        finally:
            # This block ensures that the driver is closed regardless of an exception
            if driver:
                driver.quit()
        return bin_data
