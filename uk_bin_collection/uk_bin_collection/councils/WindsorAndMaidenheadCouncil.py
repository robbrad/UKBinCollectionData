from datetime import datetime

import dateutil.parser
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
        driver = None
        try:
            data = {"bins": []}
            user_uprn = kwargs.get("uprn")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_uprn(user_uprn)

            root_url = "https://forms.rbwm.gov.uk/bincollections?uprn="
            api_url = root_url + user_uprn

            # Create Selenium webdriver
            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(api_url)

            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            # Get collections div
            next_collection_div = soup.find("div", {"class": "widget-bin-collections"})

            for tbody in next_collection_div.find_all("tbody"):
                for tr in tbody.find_all("tr"):
                    td = tr.find_all("td")
                    next_collection_type = td[0].get_text()
                    next_collection_date = dateutil.parser.parse(td[1].get_text())
                    print(next_collection_date)
                    dict_data = {
                        "type": next_collection_type,
                        "collectionDate": next_collection_date.strftime("%d/%m/%Y"),
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
