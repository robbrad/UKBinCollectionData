from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            # Create Selenium webdriver
            headless = kwargs.get("headless")
            driver = create_webdriver(kwargs.get("web_driver"), headless)
            driver.get(kwargs.get("url"))

            # Make a BS4 object
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            soup.prettify()

            data = {"bins": []}
            sections = soup.find_all("div", {"class": "wil_c-content-section_heading"})
            for s in sections:
                if s.get_text(strip=True).lower() == "bin collections":
                    rows = s.find_next_sibling(
                        "div", {"class": "c-content-section_body"}
                    ).find_all("div", {"class": "u-mb-8"})
                    for row in rows:
                        title = row.find("div", {"class": "u-mb-4"})
                        collections = row.find_all("div", {"class": "u-mb-2"})
                        if title and collections:
                            for c in collections:
                                if (
                                    c.get_text(strip=True)
                                    .lower()
                                    .startswith("next collection")
                                ):
                                    # add next collection
                                    next_collection_date = datetime.strptime(
                                        c.get_text(strip=True).replace(
                                            "Next collection - ", ""
                                        ),
                                        "%A, %d %B %Y",
                                    ).strftime(date_format)
                                    dict_data = {
                                        "type": title.get_text(strip=True).capitalize(),
                                        "collectionDate": next_collection_date,
                                    }
                                    data["bins"].append(dict_data)
                                    # add future collections without duplicating next collection
                                    future_collections = row.find(
                                        "ul", {"class": "u-mt-4"}
                                    ).find_all("li")
                                    for c in future_collections:
                                        future_collection_date = datetime.strptime(
                                            c.get_text(strip=True),
                                            "%A, %d %B %Y",
                                        ).strftime(date_format)
                                        if (
                                            future_collection_date
                                            != next_collection_date
                                        ):
                                            dict_data = {
                                                "type": title.get_text(
                                                    strip=True
                                                ).capitalize(),
                                                "collectionDate": future_collection_date,
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
