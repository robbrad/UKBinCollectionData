# alternative implementation for retrieving bin data from Kingston Upon Thames Council
# principal URL is https://waste-services.kingston.gov.uk/waste/[uprn]
# https://www.kingston.gov.uk/bins-and-recycling/collections/check-your-bin-collection-day 

# switched to using Selenium as the htmx elements are not rendered reliably with requests
# updated Jan 2026 due to small website formatting changes

import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

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

            headless = kwargs.get("headless")
            web_driver = kwargs.get("web_driver")
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(kwargs.get("url"))
            wait = WebDriverWait(driver, 15, 2)

            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "waste-service-name"))
            )

            data = {"bins": []}

            soup = BeautifulSoup(driver.page_source, "html.parser")

            service_grids = soup.find_all("div", {"class": "waste-service-grid"})
            for grid in service_grids:
                # Get the service name from the h3 within the grid
                service_name_elem = grid.find("h3", {"class": "waste-service-name"})
                if not service_name_elem:
                    continue
                service_name = service_name_elem.get_text().strip()

                summary_list = grid.find("dl", {"class": "govuk-summary-list"})
                if not summary_list:
                    continue

                rows = summary_list.find_all("div", {"class": "govuk-summary-list__row"})
                for row in rows:
                    dt = row.find("dt")
                    if dt and dt.get_text().strip().lower() == "next collection":
                        collection_date = remove_ordinal_indicator_from_date_string(
                            row.find("dd").get_text()
                        ).strip().replace(" (In progress)", "")
                        # strip out any text inside of the date string
                        collection_date = re.sub(
                            r"\n\s*\(this.*?\)", "", collection_date
                        )
                        dict_data = {
                            "type": service_name.capitalize(),
                            "collectionDate": get_next_occurrence_from_day_month(
                                datetime.strptime(
                                    collection_date
                                    + " "
                                    + datetime.now().strftime("%Y"),
                                    "%A, %d %B %Y",
                                )
                            ).strftime(date_format),
                        }
                        data["bins"].append(dict_data)

            data["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
            )

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
