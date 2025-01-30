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
        driver = None
        try:
            user_uprn = kwargs.get("uprn")
            web_driver = kwargs.get("web_driver")
            headless = kwargs.get("headless")
            check_uprn(user_uprn)
            bindata = {"bins": []}

            URI = f"https://www.teignbridge.gov.uk/repositories/hidden-pages/bin-finder?uprn={user_uprn}"

            driver = create_webdriver(web_driver, headless, None, __name__)
            driver.get(URI)

            soup = BeautifulSoup(driver.page_source, features="html.parser")

            collection_dates = soup.find_all(
                "h3"
            )  # Assuming bin types are inside <h3> tags
            bin_type_headers = soup.find_all(
                "div", {"class": "binInfoContainer"}
            )  # Assuming collection dates are inside <p> tags

            # Iterate over the results and extract bin type and collection dates
            for i, date in enumerate(collection_dates):
                collection_date = date.get_text(strip=True)

                bin_types = bin_type_headers[i].find_all("div")
                for bin_type in bin_types:
                    dict_data = {
                        "type": bin_type.text.strip(),
                        "collectionDate": datetime.strptime(
                            collection_date,
                            "%d %B %Y%A",
                        ).strftime("%d/%m/%Y"),
                    }
                    bindata["bins"].append(dict_data)

            bindata["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
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
        return bindata
